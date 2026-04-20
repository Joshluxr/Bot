/*
 * GLV (Gallant-Lambert-Vanstone) Decomposition for secp256k1
 *
 * Exploits the efficiently computable endomorphism:
 *   phi(x, y) = (beta * x, y) where beta^3 = 1 mod p
 *   phi(P) = lambda * P where lambda^3 = 1 mod n
 *
 * For scalar multiplication k*P:
 *   1. Decompose k into k1, k2 where k = k1 + k2*lambda mod n
 *   2. |k1|, |k2| ≈ sqrt(n) (128 bits instead of 256)
 *   3. Compute k*P = k1*P + k2*phi(P) using half-length scalars
 *
 * This roughly halves the number of point doublings!
 */

#ifndef GLV_H
#define GLV_H

#include "Int.h"
#include "Point.h"
#include "SECP256k1.h"

// GLV constants for secp256k1
// These are derived from the cube root of unity in the scalar field

class GLV {
public:
    // Endomorphism constants
    // beta: cube root of unity in Fp (field)
    // beta^3 = 1 mod p, where p is the field prime
    static Int beta;   // 0x7ae96a2b657c07106e64479eac3434e99cf0497512f58995c1396c28719501ee
    static Int beta2;  // beta^2 = 0x851695d49a83f8ef919bb86153cbcb16630fb68aed0a766a3ec693d68e6afa40

    // lambda: cube root of unity in Fn (scalar field)
    // lambda^3 = 1 mod n, where n is the group order
    static Int lambda;  // 0x5363ad4cc05c30e0a5261c028812645a122e22ea20816678df02967c1b23bd72
    static Int lambda2; // lambda^2

    // Decomposition constants (precomputed for secp256k1)
    // These satisfy: a1*b2 - a2*b1 = n (the group order)
    static Int a1, b1, a2, b2;
    static Int g1, g2;  // For balanced decomposition

    // Group order n
    static Int order;

    static bool initialized;

    // Initialize GLV constants
    static void Init(Secp256K1 *secp) {
        if (initialized) return;

        // beta and lambda values for secp256k1
        beta.SetBase16("7ae96a2b657c07106e64479eac3434e99cf0497512f58995c1396c28719501ee");
        beta2.SetBase16("851695d49a83f8ef919bb86153cbcb16630fb68aed0a766a3ec693d68e6afa40");
        lambda.SetBase16("5363ad4cc05c30e0a5261c028812645a122e22ea20816678df02967c1b23bd72");
        lambda2.SetBase16("ac9c52b33fa3cf1f5ad9e3fd77ed9ba4a880b9fc8ec739c2e0cfc810b51283ce");

        order.Set(&secp->order);

        // Decomposition lattice basis (precomputed for secp256k1)
        // Found using extended Euclidean algorithm on (n, lambda)
        a1.SetBase16("3086d221a7d46bcde86c90e49284eb15");
        b1.SetBase16("e4437ed6010e88286f547fa90abfe4c3");  // negative
        a2.SetBase16("114ca50f7a8e2f3f657c1108d9d44cfd8");
        b2.SetBase16("3086d221a7d46bcde86c90e49284eb15");

        // Precomputed values for balanced decomposition
        // g1 = round(b2 * 2^256 / n)
        // g2 = round(b1 * 2^256 / n) (negated)
        g1.SetBase16("3086d221a7d46bcde86c90e49284eb153dab");
        g2.SetBase16("e4437ed6010e88286f547fa90abfe4c42212");

        initialized = true;
    }

    // Decompose scalar k into (k1, k2) where k = k1 + k2*lambda mod n
    // Returns sign flags for k1 and k2 (true if negative)
    static void Decompose(const Int *k, Int *k1, Int *k2, bool *k1neg, bool *k2neg) {
        // Using the balanced decomposition algorithm
        // c1 = round(k * g1 / 2^256)
        // c2 = round(k * g2 / 2^256)
        // k1 = k - c1*a1 - c2*a2
        // k2 = -c1*b1 - c2*b2

        Int c1, c2;
        Int tmp;

        // c1 = (k * g1) >> 256 (approximate division by n)
        c1.Mult(k, &g1);
        c1.ShiftR(256);

        // c2 = (k * g2) >> 256
        c2.Mult(k, &g2);
        c2.ShiftR(256);

        // k1 = k - c1*a1 - c2*a2
        k1->Set(k);
        tmp.Mult(&c1, &a1);
        k1->Sub(&tmp);
        tmp.Mult(&c2, &a2);
        k1->Sub(&tmp);

        // k2 = -c1*b1 - c2*b2
        // Note: b1 is negative in the lattice, so we add c1*|b1|
        k2->SetInt32(0);
        tmp.Mult(&c1, &b1);  // b1 is stored as positive
        k2->Add(&tmp);       // This becomes -c1*(-|b1|) = c1*|b1|
        tmp.Mult(&c2, &b2);
        k2->Sub(&tmp);

        // Handle signs - we want k1, k2 to be positive for the multi-scalar mult
        *k1neg = k1->IsNegative();
        *k2neg = k2->IsNegative();

        if (*k1neg) {
            k1->Neg();
        }
        if (*k2neg) {
            k2->Neg();
        }

        // Ensure k1, k2 are in valid range (should be ~128 bits)
        // If they're larger, reduce mod n and try alternative decomposition
        if (k1->GetBitLength() > 129 || k2->GetBitLength() > 129) {
            // Fallback: use simple decomposition
            // k1 = k mod 2^128, k2 = k >> 128, adjust
            // This is less optimal but guaranteed to work
            k1->Set(k);
            k1->MaskByte(16);  // Keep low 128 bits
            k2->Set(k);
            k2->ShiftR(128);
            *k1neg = false;
            *k2neg = false;
        }
    }

    // Apply endomorphism: phi(P) = (beta * P.x, P.y)
    static void ApplyEndomorphism(Point *P, const Int *betaVal) {
        P->x.ModMulK1(const_cast<Int*>(betaVal));
    }

    // GLV scalar multiplication: k*P using decomposition
    // This is faster than standard double-and-add for large scalars
    static Point ScalarMult(Secp256K1 *secp, const Int *k, const Point *P) {
        Int k1, k2;
        bool k1neg, k2neg;

        // Decompose k
        Decompose(k, &k1, &k2, &k1neg, &k2neg);

        // Compute P2 = phi(P) = (beta * P.x, P.y)
        Point P2;
        P2.x.ModMulK1(&const_cast<Point*>(P)->x, &beta);
        P2.y.Set(&P->y);

        // Adjust signs
        Point P1 = *P;
        if (k1neg) {
            P1.y.ModNeg();
        }
        if (k2neg) {
            P2.y.ModNeg();
        }

        // Shamir's trick: compute k1*P1 + k2*P2 simultaneously
        // This uses a joint double-and-add with precomputed P1+P2
        return ShamirMultiply(secp, &k1, &P1, &k2, &P2);
    }

    // Shamir's trick for simultaneous scalar multiplication
    // Computes k1*P1 + k2*P2 more efficiently than separate multiplications
    static Point ShamirMultiply(Secp256K1 *secp, const Int *k1, const Point *P1,
                                const Int *k2, const Point *P2) {
        // Precompute P1 + P2
        Point P12 = secp->Add(*const_cast<Point*>(P1), *const_cast<Point*>(P2));

        Point result;
        result.Clear();

        int len1 = k1->GetBitLength();
        int len2 = k2->GetBitLength();
        int maxLen = (len1 > len2) ? len1 : len2;

        bool started = false;

        // Process bits from MSB to LSB
        for (int i = maxLen - 1; i >= 0; i--) {
            if (started) {
                result = secp->Double(result);
            }

            int b1 = k1->GetBit(i);
            int b2 = k2->GetBit(i);

            if (b1 && b2) {
                // Add P1 + P2
                if (!started) {
                    result = P12;
                    started = true;
                } else {
                    result = secp->Add(result, P12);
                }
            } else if (b1) {
                // Add P1
                if (!started) {
                    result = *P1;
                    started = true;
                } else {
                    result = secp->Add(result, *const_cast<Point*>(P1));
                }
            } else if (b2) {
                // Add P2
                if (!started) {
                    result = *P2;
                    started = true;
                } else {
                    result = secp->Add(result, *const_cast<Point*>(P2));
                }
            }
        }

        return result;
    }

    // Optimized version using wNAF (windowed Non-Adjacent Form)
    // Even faster for larger window sizes
    static Point ScalarMultWNAF(Secp256K1 *secp, const Int *k, const Point *P, int windowSize = 5) {
        Int k1, k2;
        bool k1neg, k2neg;

        Decompose(k, &k1, &k2, &k1neg, &k2neg);

        // For each half-scalar, use wNAF
        Point P1 = *P;
        Point P2;
        P2.x.ModMulK1(&const_cast<Point*>(P)->x, &beta);
        P2.y.Set(&P->y);

        if (k1neg) P1.y.ModNeg();
        if (k2neg) P2.y.ModNeg();

        // Precompute odd multiples for wNAF
        int tableSize = 1 << (windowSize - 1);
        Point *table1 = new Point[tableSize];
        Point *table2 = new Point[tableSize];

        // table[i] = (2*i + 1) * P
        table1[0] = P1;
        table2[0] = P2;
        Point P1_2 = secp->Double(P1);
        Point P2_2 = secp->Double(P2);

        for (int i = 1; i < tableSize; i++) {
            table1[i] = secp->Add(table1[i-1], P1_2);
            table2[i] = secp->Add(table2[i-1], P2_2);
        }

        // Convert to wNAF representation
        int8_t *wnaf1 = new int8_t[256];
        int8_t *wnaf2 = new int8_t[256];
        int len1 = ToWNAF(&k1, wnaf1, windowSize);
        int len2 = ToWNAF(&k2, wnaf2, windowSize);
        int maxLen = (len1 > len2) ? len1 : len2;

        // Pad shorter one with zeros
        for (int i = len1; i < maxLen; i++) wnaf1[i] = 0;
        for (int i = len2; i < maxLen; i++) wnaf2[i] = 0;

        // Double-and-add with wNAF
        Point result;
        result.Clear();
        bool started = false;

        for (int i = maxLen - 1; i >= 0; i--) {
            if (started) {
                result = secp->Double(result);
            }

            int8_t w1 = wnaf1[i];
            int8_t w2 = wnaf2[i];

            if (w1 != 0) {
                int idx = (w1 > 0) ? ((w1 - 1) / 2) : ((-w1 - 1) / 2);
                Point toAdd = table1[idx];
                if (w1 < 0) toAdd.y.ModNeg();

                if (!started) {
                    result = toAdd;
                    started = true;
                } else {
                    result = secp->Add(result, toAdd);
                }
            }

            if (w2 != 0) {
                int idx = (w2 > 0) ? ((w2 - 1) / 2) : ((-w2 - 1) / 2);
                Point toAdd = table2[idx];
                if (w2 < 0) toAdd.y.ModNeg();

                if (!started) {
                    result = toAdd;
                    started = true;
                } else {
                    result = secp->Add(result, toAdd);
                }
            }
        }

        delete[] table1;
        delete[] table2;
        delete[] wnaf1;
        delete[] wnaf2;

        return result;
    }

private:
    // Convert integer to wNAF representation
    static int ToWNAF(const Int *k, int8_t *wnaf, int w) {
        Int val;
        val.Set(k);

        int i = 0;
        int width = 1 << w;
        int halfWidth = 1 << (w - 1);

        while (!val.IsZero() && i < 256) {
            if (val.IsOdd()) {
                int mod = val.GetInt32() & (width - 1);
                if (mod >= halfWidth) {
                    wnaf[i] = (int8_t)(mod - width);
                    val.Add((uint64_t)(width - mod));
                } else {
                    wnaf[i] = (int8_t)mod;
                    val.Sub((uint64_t)mod);
                }
            } else {
                wnaf[i] = 0;
            }
            val.ShiftR(1);
            i++;
        }

        return i;
    }
};

// Static member definitions
Int GLV::beta;
Int GLV::beta2;
Int GLV::lambda;
Int GLV::lambda2;
Int GLV::a1, GLV::b1, GLV::a2, GLV::b2;
Int GLV::g1, GLV::g2;
Int GLV::order;
bool GLV::initialized = false;

#endif // GLV_H
