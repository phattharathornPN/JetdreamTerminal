#include <stdio.h>
#include <string.h>
#include "d3des.h"

static unsigned char d3desObfuscationKey[] = {23,82,107,6,35,78,88,7};

int main(int argc, char **argv) {
    if (argc < 2) return 1;
    unsigned char buf[8];
    memset(buf, 0, 8);
    strncpy((char*)buf, argv[1], 8);
    deskey(d3desObfuscationKey, EN0);
    des(buf, buf);
    fwrite(buf, 1, 8, stdout);
    return 0;
}
