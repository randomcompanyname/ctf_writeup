---

title: flag
link: http://pwnable.kr/bin/flag

---

This executable is stripped and unusable righ now, but there is somthing in the strings:

    $ strings flag
    ...
    $Info: This file is packed with the UPX executable packer http://upx.sf.net $
    ...

We need to unpack the executable first:

    upx -d flag

Now we can analyse the file:

    $ gdb flag
    (gdb) disass main

    Dump of assembler code for function main:
       0x0000000000401164 <+0>:     push   %rbp
       0x0000000000401165 <+1>:     mov    %rsp,%rbp
       0x0000000000401168 <+4>:     sub    $0x10,%rsp
       0x000000000040116c <+8>:     mov    $0x496658,%edi
       0x0000000000401171 <+13>:    callq  0x402080 <puts>
       0x0000000000401176 <+18>:    mov    $0x64,%edi
       0x000000000040117b <+23>:    callq  0x4099d0 <malloc>
       0x0000000000401180 <+28>:    mov    %rax,-0x8(%rbp)
       0x0000000000401184 <+32>:    mov    0x2c0ee5(%rip),%rdx        # 0x6c2070 <flag>
       0x000000000040118b <+39>:    mov    -0x8(%rbp),%rax
       0x000000000040118f <+43>:    mov    %rdx,%rsi
       0x0000000000401192 <+46>:    mov    %rax,%rdi
       0x0000000000401195 <+49>:    callq  0x400320
       0x000000000040119a <+54>:    mov    $0x0,%eax
       0x000000000040119f <+59>:    leaveq
       0x00000000004011a0 <+60>:    retq

So something is going on at `0x6c2070`:

    (gdb) x/wx 0x6c2070
    0x6c2070 <flag>:        0x00496628

    (gdb) x/s 0x00496628
    0x496628:       "UPX...? sounds like a delivery service :)"

> "UPX...? sounds like a delivery service :)"
