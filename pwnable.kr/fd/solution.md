---

title: fd
link: ssh fd@pwnable.kr -p2222 (pw:guest)

---

The flag file is reserved for the fd_pwn user, and we could access it via the `fd` program:

    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    char buf[32];
    int main(int argc, char* argv[], char* envp[]){
            if(argc<2){
                    printf("pass argv[1] a number\n");
                    return 0;
            }
            int fd = atoi( argv[1] ) - 0x1234;
            int len = 0;
            len = read(fd, buf, 32);
            if(!strcmp("LETMEWIN\n", buf)){
                    printf("good job :)\n");
                    system("/bin/cat flag");
                    exit(0);
            }
            printf("learn about Linux file IO\n");
            return 0;

    }

We can see that we try to read from the file descriptor `atoi( argv[1] ) - 0x1234` and expect to have the content `LETMEWIN`.
With the `read` function, if we use the file descriptor `0`, it will use the standart input, we we can type what we want.

`0x1234` is `4660` in decimal, so let's try this:

    fd@ubuntu:~$ ./fd 4660
    LETMEWIN
    good job :)
    mommy! I think I know what a file descriptor is!!

>  mommy! I think I know what a file descriptor is!!
