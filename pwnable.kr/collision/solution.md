---

title: collision
link: ssh col@pwnable.kr -p2222 (pw:guest)

---

This time, the input for the program is a string of 20 chars, and it sum needs to be equal to `0x21DD09EC`.

This number is not divisible by 5, so we can't send 5 times the same string composed of this number/5.

Plus, we can't use any `\x00` in the string because it would break the strlen sooner than the end of the string. We can work around this way:

    >>> hex(0x21DD09EC - 0x04040404)
    '0x1dd905e8'

So we know we can send `0x1dd905e8` and then 4 times `0x01010101`:

    >>> hex(0x1dd905e8 + 0x01010101 * 4)
    '0x21dd09ec'

Then, with the executable, inverting the number according to the little endianness:

    ./col $(python -c "print '\x01'*4*4 + '\xe8\x05\xd9\x1d'")
    daddy! I just managed to create a hash collision :)

> daddy! I just managed to create a hash collision :)
