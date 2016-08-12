---

title: Level 2
link: ssh level2@io.netgarage.org

---

    $ ./level02
    source code is available in level02.c

Opening the `level02.c` file we can see:

1. The number of args must be 2, (`argv[0]` being the caller's name).
2. The two arguments should be numbers
3. The `catcher` function will be called on the event `SIGFPE` (launched for example for a division by 0)
4. The return value of the function is `argv[1]/argv[2]`

If the `catcher` function is called, it will set the current user identity, and print a win message, before spawning a new shell.
This is clearly the indication that we need to raise a `SIGFPE` exception.

The `SIGFPE` can me triggered with a `1/0` or a `sqrt(-1)` for example, in our case, neither can be used.

What we can do instead is try to use an integer value outside of the bound of the integer definition.
We can see on [the `abs` reference page](http://en.cppreference.com/w/c/numeric/math/abs) that the most-negative value to be out of range is `-2147483648`, because this will convert to `2147483648`, above the MAX_INT value. So if we send to `abs` the value `- 2147483648`, the result will be also `-2147483648` (because of binary max bound and negative values).

But, if we send the value `2147483648` to `abs`, which is an incorrect value, it should raise an error:

    $ ./level02 "-2147483648" "-1"
    source code is available in level02.c

    WIN!

Level 3 password: `OlhCmdZKbuzqngfz`


