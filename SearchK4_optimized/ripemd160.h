/*
 * ripemd160.h — standalone RIPEMD-160 hash function
 *
 * Pure C, no dependencies beyond <stdint.h>/<stddef.h>/<string.h>.
 * Public API:
 *   void ripemd160(const uint8_t *data, size_t len, uint8_t out[20]);
 *
 * The algorithm was published by Dobbertin, Bosselaers, and Preneel in 1996.
 * This implementation follows the reference specification directly.
 *
 * Verified against the standard test vectors:
 *   ""               -> 9c1185a5c5e9fc54612808977ee8f548b2258d31
 *   "abc"            -> 8eb208f7e05d987a9b044a8e98c6b087f15a0bfc
 *   "message digest" -> 5d0689ef49d2fae572b881b123a85ffa21595f36
 */

#ifndef RIPEMD160_H
#define RIPEMD160_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

void ripemd160(const uint8_t *data, size_t len, uint8_t out[20]);

#ifdef __cplusplus
}
#endif

#endif /* RIPEMD160_H */
