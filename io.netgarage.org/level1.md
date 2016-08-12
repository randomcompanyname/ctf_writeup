---

title: Level 1
link: ssh level1@io.netgarage.org

---


Running `level01` ask for a 3 digits number which we will find inside the binary.

Running the `strings` utility (used to find... well strings in binary files) reveal nothing:

    $ strings level01
    ,0<     w
    Enter the 3 digit passcode to enter: Congrats you found it, now read the password for level2 from /home/level2/.pass
    /bin/sh
    .symtab
    .strtab
    .shstrtab
    .text
    .lib
    .data
    level01.asm
    ...
    _end

Launching the program under gdb:

    $ gdb level01

Show the disassembly code for the main function (entry point of the program)

    (gdb) disassemble main
    Dump of assembler code for function main:
       0x08048080 <+0>:     push   $0x8049128
       0x08048085 <+5>:     call   0x804810f
       0x0804808a <+10>:    call   0x804809f
       0x0804808f <+15>:    cmp    $0x10f,%eax
       0x08048094 <+20>:    je     0x80480dc
       0x0804809a <+26>:    call   0x8048103
    End of assembler dump.

Another way to see the disassembly code is to use

    $ objdump -d level01

    level01:     file format elf32-i386


    Disassembly of section .text:

    08048080 <_start>:
     8048080:       68 28 91 04 08          push   $0x8049128
     8048085:       e8 85 00 00 00          call   804810f <puts>
     804808a:       e8 10 00 00 00          call   804809f <fscanf>
     804808f:       3d 0f 01 00 00          cmp    $0x10f,%eax
     8048094:       0f 84 42 00 00 00       je     80480dc <YouWin>
     804809a:       e8 64 00 00 00          call   8048103 <exit>

The first call print the question with `puts`.
The second one ask for the user input (the password.
Then the program compare a fixed value with the value of the register `eax`.

This value is a hexadecimal value, we can display its decimal value with `p` in gdb:

    (gdb) p 0x10f
    $1 = 271

So apparently we are comparing the entered value, which is stored in the `eax` register.

`je` will jump to the label if the values are equal, since this jump is to the `YouWin` section, we can assume the password is `271`.

    $ ./level01
    Enter the 3 digit passcode to enter: 271
    Congrats you found it, now read the password for level2 from /home/level2/.pass

The password for level2 is `XNWFtWKWHhaaXoKI`.


