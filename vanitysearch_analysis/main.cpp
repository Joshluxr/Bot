/*
 * This file is part of the VanitySearch distribution (https://github.com/JeanLucPons/VanitySearch).
 * Copyright (c) 2019 Jean Luc PONS.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
*/

#include "Timer.h"
#include "Vanity.h"
#include "SECP256k1.h"
#include <fstream>
#include <string>
#include <string.h>
#include <stdexcept>
#include "hash/sha512.h"
#include "hash/sha256.h"

#define RELEASE "1.20-optimized"

using namespace std;

// Forward declaration for keyspace parsing (from allinbit/VanitySearch)
void getKeySpace(const string& text, BITCRACK_PARAM* bc, Int& maxKey);
void checkKeySpace(BITCRACK_PARAM* bc, Int& maxKey);

// ------------------------------------------------------------------------------------------

void printUsage() {

  printf("VanitySearch v" RELEASE " - Optimized with FixedPaul/allinbit/Telariust features\n\n");
  printf("VanitySearch [-check] [-v] [-u] [-b] [-c] [-gpu] [-stop] [-i inputfile]\n");
  printf("             [-gpuId gpuId1[,gpuId2,...]] [-g g1x,g1y,[,g2x,g2y,...]]\n");
  printf("             [-o outputfile] [-m maxFound] [-ps seed] [-s seed] [-t nbThread]\n");
  printf("             [-nosse] [-r rekey] [-check] [-kp] [-sp startPubKey]\n");
  printf("             [--keyspace START:END] [-rp privkey partialkeyfile] [prefix]\n\n");
  printf(" prefix: prefix to search (Can contain wildcard '?' or '*')\n");
  printf(" -v: Print version\n");
  printf(" -u: Search uncompressed addresses\n");
  printf(" -b: Search both uncompressed or compressed addresses\n");
  printf(" -c: Case insensitive search\n");
  printf(" -gpu: Enable GPU calculation\n");
  printf(" -stop: Stop when all prefixes are found\n");
  printf(" -i inputfile: Get list of prefixes/addresses to search from file (multi-address mode)\n");
  printf(" -o outputfile: Output results to the specified file\n");
  printf(" -gpuId gpuId1,gpuId2,...: List of GPU(s) to use, default is 0\n");
  printf(" -g g1x,g1y,g2x,g2y, ...: Specify GPU(s) kernel gridsize, default is 8*(MP number),128\n");
  printf(" -m: Specify maximum number of prefixes found by each kernel call\n");
  printf(" -s seed: Specify a seed for the base key, default is random\n");
  printf(" -ps seed: Specify a seed concatenated with a crypto secure random seed (paranoiac mode)\n");
  printf(" -t threadNumber: Specify number of CPU threads, default is number of cores\n");
  printf(" -nosse: Disable SSE hash function\n");
  printf(" -l: List CUDA enabled devices\n");
  printf(" -check: Check CPU and GPU kernel vs CPU\n");
  printf(" -cp privKey: Compute public key (privKey in hex format)\n");
  printf(" -ca pubKey: Compute address (pubKey in hex format)\n");
  printf(" -kp: Generate key pair\n");
  printf(" -rp privkey partialkeyfile: Reconstruct final private key(s) from partial key(s) info.\n");
  printf(" -sp startPubKey: Start the search with a pubKey (for private key splitting)\n");
  printf(" -r rekey: Rekey interval in MegaKey, default is disabled\n");
  printf("\n");
  printf("NEW FEATURES (from allinbit/VanitySearch):\n");
  printf(" --keyspace START:END    Search within the specified keyspace range\n");
  printf(" --keyspace START:+COUNT Search COUNT keys starting from START\n");
  printf(" --keyspace :+COUNT      Search COUNT keys starting from 1\n");
  printf(" --keyspace :END         Search from 1 to END\n");
  printf("   Where START, END, COUNT are in hex format (up to 64 chars)\n");
  printf("   Example: --keyspace 1000000:2000000\n");
  printf("   Example: --keyspace 8000000000000000:+1000000000000000\n");
  exit(0);

}

// ------------------------------------------------------------------------------------------

int getInt(string name,char *v) {

  int r;

  try {

    r = std::stoi(string(v));

  } catch(std::invalid_argument&) {

    printf("Invalid %s argument, number expected\n",name.c_str());
    exit(-1);

  }

  return r;

}

// ------------------------------------------------------------------------------------------

void getInts(string name,vector<int> &tokens, const string &text, char sep) {

  size_t start = 0, end = 0;
  tokens.clear();
  int item;

  try {

    while ((end = text.find(sep, start)) != string::npos) {
      item = std::stoi(text.substr(start, end - start));
      tokens.push_back(item);
      start = end + 1;
    }

    item = std::stoi(text.substr(start));
    tokens.push_back(item);

  } catch(std::invalid_argument &) {

    printf("Invalid %s argument, number expected\n",name.c_str());
    exit(-1);

  }

}

// ------------------------------------------------------------------------------------------

void parseFile(string fileName, vector<string> &lines) {

  // Get file size
  FILE *fp = fopen(fileName.c_str(), "rb");
  if (fp == NULL) {
    printf("Error: Cannot open %s %s\n", fileName.c_str(), strerror(errno));
    exit(-1);
  }
  fseek(fp, 0L, SEEK_END);
  size_t sz = ftell(fp);
  size_t nbAddr = sz / 33; /* Upper approximation */
  bool loaddingProgress = sz > 100000;
  fclose(fp);

  // Parse file
  int nbLine = 0;
  string line;
  ifstream inFile(fileName);
  lines.reserve(nbAddr);
  while (getline(inFile, line)) {

    // Remove ending \r\n
    int l = (int)line.length() - 1;
    while (l >= 0 && isspace(line.at(l))) {
      line.pop_back();
      l--;
    }

    if (line.length() > 0) {
      lines.push_back(line);
      nbLine++;
      if (loaddingProgress) {
        if ((nbLine % 50000) == 0)
          printf("[Loading input file %5.1f%%]\r", ((double)nbLine*100.0) / ((double)(nbAddr)*33.0 / 34.0));
      }
    }

  }

  if (loaddingProgress)
    printf("[Loading input file 100.0%%]\n");

}

// ------------------------------------------------------------------------------------------

void generateKeyPair(Secp256K1 *secp, string seed, int searchMode,bool paranoiacSeed) {

  if (seed.length() < 8) {
    printf("Error: Use a seed of at least 8 characters to generate a key pair\n");
    printf("Ex: VanitySearch -s \"A Strong Password\" -kp\n");
    exit(-1);
  }

  if(paranoiacSeed)
    seed = seed + Timer::getSeed(32);

  if (searchMode == SEARCH_BOTH) {
    printf("Error: Use compressed or uncompressed to generate a key pair\n");
    exit(-1);
  }

  bool compressed = (searchMode == SEARCH_COMPRESSED);

  string salt = "VanitySearch";
  unsigned char hseed[64];
  pbkdf2_hmac_sha512(hseed, 64, (const uint8_t *)seed.c_str(), seed.length(),
    (const uint8_t *)salt.c_str(), salt.length(),
    2048);

  Int privKey;
  privKey.SetInt32(0);
  sha256(hseed, 64, (unsigned char *)privKey.bits64);
  Point p = secp->ComputePublicKey(&privKey);
  printf("Priv : %s\n", secp->GetPrivAddress(compressed,privKey).c_str());
  printf("Pub  : %s\n", secp->GetPublicKeyHex(compressed,p).c_str());

}

// ------------------------------------------------------------------------------------------

void outputAdd(string outputFile, int addrType, string addr, string pAddr, string pAddrHex) {

  FILE *f = stdout;
  bool needToClose = false;

  if (outputFile.length() > 0) {
    f = fopen(outputFile.c_str(), "a");
    if (f == NULL) {
      printf("Cannot open %s for writing\n", outputFile.c_str());
      f = stdout;
    } else {
      needToClose = true;
    }
  }

  fprintf(f, "\nPub Addr: %s\n", addr.c_str());


  switch (addrType) {
  case P2PKH:
    fprintf(f, "Priv (WIF): p2pkh:%s\n", pAddr.c_str());
    break;
  case P2SH:
    fprintf(f, "Priv (WIF): p2wpkh-p2sh:%s\n", pAddr.c_str());
    break;
  case BECH32:
    fprintf(f, "Priv (WIF): p2wpkh:%s\n", pAddr.c_str());
    break;
  }
  fprintf(f, "Priv (HEX): 0x%s\n", pAddrHex.c_str());

  if (needToClose)
    fclose(f);

}

// ------------------------------------------------------------------------------------------
#define CHECK_ADDR()                                           \
  fullPriv.ModAddK1order(&e, &partialPrivKey);                 \
  p = secp->ComputePublicKey(&fullPriv);                       \
  cAddr = secp->GetAddress(addrType, compressed, p);           \
  if (cAddr == addr) {                                         \
    found = true;                                              \
    string pAddr = secp->GetPrivAddress(compressed, fullPriv); \
    string pAddrHex = fullPriv.GetBase16();                    \
    outputAdd(outputFile, addrType, addr, pAddr, pAddrHex);    \
  }

void reconstructAdd(Secp256K1 *secp, string fileName, string outputFile, string privAddr) {

  bool compressed;
  int addrType;
  Int lambda;
  Int lambda2;
  lambda.SetBase16("5363ad4cc05c30e0a5261c028812645a122e22ea20816678df02967c1b23bd72");
  lambda2.SetBase16("ac9c52b33fa3cf1f5ad9e3fd77ed9ba4a880b9fc8ec739c2e0cfc810b51283ce");

  Int privKey = secp->DecodePrivateKey((char *)privAddr.c_str(),&compressed);
  if(privKey.IsNegative())
    exit(-1);

  vector<string> lines;
  parseFile(fileName,lines);

  for (int i = 0; i < (int)lines.size(); i+=2) {

    string addr;
    string partialPrivAddr;

    if (lines[i].substr(0, 12) == "PubAddress: ") {

      addr = lines[i].substr(12);

      switch (addr.data()[0]) {
      case '1':
        addrType = P2PKH; break;
      case '3':
        addrType = P2SH; break;
      case 'b':
      case 'B':
        addrType = BECH32; break;
      default:
        printf("Invalid partialkey info file at line %d\n", i);
        printf("%s Address format not supported\n", addr.c_str());
        continue;
      }

    } else {
      printf("Invalid partialkey info file at line %d (\"PubAddress: \" expected)\n",i);
      exit(-1);
    }

    if (lines[i+1].substr(0, 13) == "PartialPriv: ") {
      partialPrivAddr = lines[i+1].substr(13);
    } else {
      printf("Invalid partialkey info file at line %d (\"PartialPriv: \" expected)\n", i);
      exit(-1);
    }

    bool partialMode;
    Int partialPrivKey = secp->DecodePrivateKey((char *)partialPrivAddr.c_str(), &partialMode);
    if (privKey.IsNegative()) {
      printf("Invalid partialkey info file at line %d\n", i);
      exit(-1);
    }

    if (partialMode != compressed) {

      printf("Warning, Invalid partialkey at line %d (Wrong compression mode, ignoring key)\n", i);
      continue;

    } else {

      // Reconstruct the address
      Int fullPriv;
      Point p;
      Int e;
      string cAddr;
      bool found = false;

      // No sym, no endo
      e.Set(&privKey);
      CHECK_ADDR();

      // No sym, endo 1
      e.Set(&privKey);
      e.ModMulK1order(&lambda);
      CHECK_ADDR();

      // No sym, endo 2
      e.Set(&privKey);
      e.ModMulK1order(&lambda2);
      CHECK_ADDR();

      // sym, no endo
      e.Set(&privKey);
      e.Neg();
      e.Add(&secp->order);
      CHECK_ADDR();

      // sym, endo 1
      e.Set(&privKey);
      e.ModMulK1order(&lambda);
      e.Neg();
      e.Add(&secp->order);
      CHECK_ADDR();

      // sym, endo 2
      e.Set(&privKey);
      e.ModMulK1order(&lambda2);
      e.Neg();
      e.Add(&secp->order);
      CHECK_ADDR();

      if (!found) {
        printf("Unable to reconstruct final key from partialkey line %d\n Addr: %s\n PartKey: %s\n",
          i, addr.c_str(),partialPrivAddr.c_str());
      }

    }

  }

}

// ------------------------------------------------------------------------------------------
// Keyspace/Range parsing functions (from allinbit/VanitySearch)
// Supports BitCrack-style keyspace specification:
//   --keyspace START:END
//   --keyspace START:+COUNT
//   --keyspace :+COUNT
//   --keyspace :END
// ------------------------------------------------------------------------------------------

void getKeySpace(const string& text, BITCRACK_PARAM* bc, Int& maxKey) {
  size_t start = 0, end = 0;
  string item;

  try {
    if ((end = text.find(':', start)) != string::npos) {
      item = string(text.substr(start, end));
      start = end + 1;
    } else {
      item = string(text);
    }

    // Parse START
    if (item.length() == 0) {
      bc->ksStart.SetInt32(1);
    } else if (item.length() > 64) {
      printf("Error: keyspace START invalid (max 64 hex chars)\n");
      exit(-1);
    } else {
      item.insert(0, 64 - item.length(), '0');
      for (int i = 0; i < 32; i++) {
        unsigned char ch = 0;
        sscanf(&item[2 * i], "%02hhX", &ch);
        bc->ksStart.SetByte(31 - i, ch);
      }
    }

    // Parse END or +COUNT
    if (start != 0 && (end = text.find('+', start)) != string::npos) {
      // START:+COUNT format
      item = string(text.substr(end + 1));
      if (item.length() > 64 || item.length() == 0) {
        printf("Error: keyspace COUNT invalid (max 64 hex chars)\n");
        exit(-1);
      }

      item.insert(0, 64 - item.length(), '0');
      for (int i = 0; i < 32; i++) {
        unsigned char ch = 0;
        sscanf(&item[2 * i], "%02hhX", &ch);
        bc->ksFinish.SetByte(31 - i, ch);
      }
      bc->ksFinish.Add(&bc->ksStart);
    } else if (start != 0) {
      // START:END format
      item = string(text.substr(start));
      if (item.length() > 64 || item.length() == 0) {
        printf("Error: keyspace END invalid (max 64 hex chars)\n");
        exit(-1);
      }

      item.insert(0, 64 - item.length(), '0');
      for (int i = 0; i < 32; i++) {
        unsigned char ch = 0;
        sscanf(&item[2 * i], "%02hhX", &ch);
        bc->ksFinish.SetByte(31 - i, ch);
      }
    } else {
      // No END specified, use maxKey
      bc->ksFinish.Set(&maxKey);
    }
  } catch (std::invalid_argument&) {
    printf("Error: Invalid --keyspace argument\n");
    exit(-1);
  }
}

void checkKeySpace(BITCRACK_PARAM* bc, Int& maxKey) {
  if (bc->ksStart.IsGreater(&maxKey) || bc->ksFinish.IsGreater(&maxKey)) {
    printf("Error: START/END exceeds max key %s\n", maxKey.GetBase16().c_str());
    exit(-1);
  }

  if (bc->ksFinish.IsLowerOrEqual(&bc->ksStart)) {
    printf("Error: END must be greater than START\n");
    exit(-1);
  }

  if (bc->ksFinish.IsLowerOrEqual(&bc->ksNext)) {
    printf("Error: END must be greater than NEXT\n");
    exit(-1);
  }
}

// ------------------------------------------------------------------------------------------

int main(int argc, char* argv[]) {

  // Global Init
  Timer::Init();
  rseed(Timer::getSeed32());

  // Init SecpK1
  Secp256K1 *secp = new Secp256K1();
  secp->Init();

  // Browse arguments
  if (argc < 2) {
    printf("Error: No arguments (use -h for help)\n");
    exit(-1);
  }

  int a = 1;
  bool gpuEnable = false;
  bool stop = false;
  int searchMode = SEARCH_COMPRESSED;
  vector<int> gpuId = {0};
  vector<int> gridSize;
  string seed = "";
  vector<string> prefix;
  string outputFile = "";
  int nbCPUThread = Timer::getCoreNumber();
  bool tSpecified = false;
  bool sse = true;
  uint32_t maxFound = 65536;
  uint64_t rekey = 0;
  Point startPuKey;
  startPuKey.Clear();
  bool startPubKeyCompressed;
  bool caseSensitive = true;
  bool paranoiacSeed = false;

  // BitCrack-style keyspace range support (from allinbit/VanitySearch)
  BITCRACK_PARAM bitcrackRange;
  BITCRACK_PARAM* keyspaceRange = NULL;
  Int maxKey;
  maxKey.SetBase16("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140");
  bitcrackRange.ksStart.SetInt32(1);
  bitcrackRange.ksNext.Set(&bitcrackRange.ksStart);
  bitcrackRange.ksFinish.Set(&maxKey);

  while (a < argc) {

    if (strcmp(argv[a], "-gpu")==0) {
      gpuEnable = true;
      a++;
    } else if (strcmp(argv[a], "-gpuId")==0) {
      a++;
      getInts("gpuId",gpuId,string(argv[a]),',');
      a++;
    } else if (strcmp(argv[a], "-stop") == 0) {
      stop = true;
      a++;
    } else if (strcmp(argv[a], "-c") == 0) {
      caseSensitive = false;
      a++;
    } else if (strcmp(argv[a], "-v") == 0) {
      printf("%s\n",RELEASE);
      exit(0);
    } else if (strcmp(argv[a], "-check") == 0) {

      Int::Check();
      secp->Check();

#ifdef WITHGPU
      if (gridSize.size() == 0) {
        gridSize.push_back(-1);
        gridSize.push_back(128);
      }
      GPUEngine g(gridSize[0],gridSize[1],gpuId[0],maxFound,false);
      g.SetSearchMode(searchMode);
      g.Check(secp);
#else
  printf("GPU code not compiled, use -DWITHGPU when compiling.\n");
#endif
      exit(0);
    } else if (strcmp(argv[a], "-l") == 0) {

#ifdef WITHGPU
      GPUEngine::PrintCudaInfo();
#else
  printf("GPU code not compiled, use -DWITHGPU when compiling.\n");
#endif
      exit(0);

    } else if (strcmp(argv[a], "-kp") == 0) {
      generateKeyPair(secp,seed,searchMode,paranoiacSeed);
      exit(0);
    } else if (strcmp(argv[a], "-sp") == 0) {
      a++;
      string pub = string(argv[a]);
      startPuKey = secp->ParsePublicKeyHex(pub, startPubKeyCompressed);
      a++;
    } else if(strcmp(argv[a],"-ca") == 0) {
      a++;
      string pub = string(argv[a]);
      bool isComp;
      Point p = secp->ParsePublicKeyHex(pub,isComp);
      printf("Addr (P2PKH): %s\n",secp->GetAddress(P2PKH,isComp,p).c_str());
      printf("Addr (P2SH): %s\n",secp->GetAddress(P2SH,isComp,p).c_str());
      printf("Addr (BECH32): %s\n",secp->GetAddress(BECH32,isComp,p).c_str());
      exit(0);
    } else if (strcmp(argv[a], "-cp") == 0) {
      a++;
      string priv = string(argv[a]);
      Int k;
      bool isComp = true;
      if(priv[0]=='5' || priv[0] == 'K' || priv[0] == 'L') {
        k = secp->DecodePrivateKey((char *)priv.c_str(),&isComp);
      } else {
        k.SetBase16(argv[a]);
      }
      Point p = secp->ComputePublicKey(&k);
      printf("PrivAddr: p2pkh:%s\n",secp->GetPrivAddress(isComp,k).c_str());
      printf("PubKey: %s\n",secp->GetPublicKeyHex(isComp,p).c_str());
      printf("Addr (P2PKH): %s\n", secp->GetAddress(P2PKH,isComp,p).c_str());
      printf("Addr (P2SH): %s\n", secp->GetAddress(P2SH,isComp,p).c_str());
      printf("Addr (BECH32): %s\n", secp->GetAddress(BECH32,isComp,p).c_str());
      exit(0);
    } else if (strcmp(argv[a], "-rp") == 0) {
      a++;
      string priv = string(argv[a]);
      a++;
      string file = string(argv[a]);
      a++;
      reconstructAdd(secp,file,outputFile,priv);
      exit(0);
    } else if (strcmp(argv[a], "-u") == 0) {
      searchMode = SEARCH_UNCOMPRESSED;
      a++;
    } else if (strcmp(argv[a], "-b") == 0) {
      searchMode = SEARCH_BOTH;
      a++;
    } else if (strcmp(argv[a], "-nosse") == 0) {
      sse = false;
      a++;
    } else if (strcmp(argv[a], "-g") == 0) {
      a++;
      getInts("gridSize",gridSize,string(argv[a]),',');
      a++;
    } else if (strcmp(argv[a], "-s") == 0) {
      a++;
      seed = string(argv[a]);
      a++;
    } else if (strcmp(argv[a], "-ps") == 0) {
      a++;
      seed = string(argv[a]);
      paranoiacSeed = true;
      a++;
    } else if (strcmp(argv[a], "-o") == 0) {
      a++;
      outputFile = string(argv[a]);
      a++;
    } else if (strcmp(argv[a], "-i") == 0) {
      a++;
      parseFile(string(argv[a]),prefix);
      a++;
    } else if (strcmp(argv[a], "-t") == 0) {
      a++;
      nbCPUThread = getInt("nbCPUThread",argv[a]);
      a++;
      tSpecified = true;
    } else if (strcmp(argv[a], "-m") == 0) {
      a++;
      maxFound = getInt("maxFound", argv[a]);
      a++;
    } else if (strcmp(argv[a], "-r") == 0) {
      a++;
      rekey = (uint64_t)getInt("rekey", argv[a]);
      a++;
    } else if (strcmp(argv[a], "--keyspace") == 0) {
      // BitCrack-style keyspace range (from allinbit/VanitySearch)
      a++;
      getKeySpace(string(argv[a]), &bitcrackRange, maxKey);
      bitcrackRange.ksNext.Set(&bitcrackRange.ksStart);
      keyspaceRange = &bitcrackRange;
      a++;
    } else if (strcmp(argv[a], "-h") == 0) {
      printUsage();
    } else if (a == argc - 1) {
      prefix.push_back(string(argv[a]));
      a++;
    } else {
      printf("Unexpected %s argument\n",argv[a]);
      exit(-1);
    }

  }

  printf("VanitySearch v" RELEASE "\n");
  printf("Optimizations: UMultSpecial, ModSub256isOdd, BatchGPUInit, KeyspaceRange\n");

  if(gridSize.size()==0) {
    for (int i = 0; i < gpuId.size(); i++) {
      gridSize.push_back(-1);
      gridSize.push_back(128);
    }
  } else if(gridSize.size() != gpuId.size()*2) {
    printf("Invalid gridSize or gpuId argument, must have coherent size\n");
    exit(-1);
  }

  // Validate and display keyspace range if specified
  if (keyspaceRange != NULL) {
    checkKeySpace(keyspaceRange, maxKey);
    printf("[Keyspace Range Mode]\n");
    printf("  Start: %s\n", keyspaceRange->ksStart.GetBase16().c_str());
    printf("  End:   %s\n", keyspaceRange->ksFinish.GetBase16().c_str());
  }

  // Let one CPU core free per gpu is gpu is enabled
  // It will avoid to hang the system
  if( !tSpecified && nbCPUThread>1 && gpuEnable)
    nbCPUThread-=(int)gpuId.size();
  if(nbCPUThread<0)
    nbCPUThread = 0;

  // If a starting public key is specified, force the search mode according to the key
  if (!startPuKey.isZero()) {
    searchMode = (startPubKeyCompressed)?SEARCH_COMPRESSED:SEARCH_UNCOMPRESSED;
  }

  VanitySearch *v = new VanitySearch(secp, prefix, seed, searchMode, gpuEnable, stop, outputFile, sse,
    maxFound, rekey, caseSensitive, startPuKey, paranoiacSeed);

  // Pass keyspace range to VanitySearch if specified
  if (keyspaceRange != NULL) {
    v->useKeyspaceRange = true;
    v->keyspaceRange = keyspaceRange;
  } else {
    v->useKeyspaceRange = false;
    v->keyspaceRange = NULL;
  }

  v->Search(nbCPUThread,gpuId,gridSize);

  return 0;
}
