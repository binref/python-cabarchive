#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: LGPL-2.1+

import cabarchive as cab
import datetime
import subprocess
import time
import hashlib


def check_archive(filename: str, expected_rc: int = 0):
    argv = ["cabextract", "--test", filename]
    rc = subprocess.call(argv)
    assert rc == expected_rc, "invalid return code: %r" % rc


def check_range(data: bytes, expected: bytes):
    assert data
    assert expected
    failures = 0
    if len(data) != len(expected):
        print("different sizes, got %i expected %i" % (len(data), len(expected)))
        failures += 1
    for i in range(0, len(data)):
        if data[i] != expected[i]:
            print("@0x%02x got 0x%02x expected 0x%02x" % (i, data[i], expected[i]))
            failures += 1
            if failures > 10:
                print("More than 10 failures, giving up...")
                break
    assert failures == 0, "Data is not the same"


def main():

    # parse junk
    arc = cab.CabArchive()
    try:
        arc.parse(b"hello")
    except cab.CorruptionError:
        pass

    # parse junk
    check_archive("hello", expected_rc=1)

    # test checksum function
    csum = cab.archive._checksum_compute(b"hello123")
    assert csum == 0x5F5E5407, "0x%04x" % csum
    csum = cab.archive._checksum_compute(b"hello")
    assert csum == 0x6C6C6507, "0x%04x" % csum

    # measure speed
    data = open("data/random.bin", "rb").read()
    start = time.time()
    csum = cab.archive._checksum_compute(data)
    print("profile checksum: %fms" % ((time.time() - start) * 1000))

    # parse test files
    for fn in [
        "data/simple.cab",
        "data/compressed.cab",
        "data/utf8.cab",
        "data/large.cab",
        "data/large-compressed.cab",
    ]:
        arc = cab.CabArchive()
        print("Parsing:", fn)
        old = open(fn, "rb").read()
        arc.parse(old)
        assert len(arc.files) == 1
        if arc.find_file("*.txt"):
            cff = arc.files[0]
            assert cff.filename == "test.txt", cff.filename
            assert cff.contents == b"test123", cff.contents
            assert len(cff.contents) == 7, "Expected 7, got %i" % len(cff.contents)
            assert cff.date.year == 2015
        elif arc.find_file("*.dat"):
            cff = arc.files[0]
            assert cff.filename == "tést.dat", cff.filename
            assert cff.contents == "tést123".encode(), cff.contents
            assert len(cff.contents) == 8, "Expected 8, got %i" % len(cff.contents)
            assert cff.date.year == 2015
        else:
            cff = arc.files[0]
            assert cff.filename == "random.bin", cff.filename
            assert len(cff.contents) == 0xFFFFF, "Expected 1 Mb, got %i" % len(
                cff.contents
            )
            assert (
                hashlib.sha1(cff.contents).hexdigest()
                == "8497fe89c41871e3cbd7955e13321e056dfbd170"
            ), "SHA hash incorrect"
            assert cff.date.year == 2015

        # make sure we don't modify on roundtrip
        compressed = False
        if fn.find("compressed") != -1:
            compressed = True
        new = arc.save(compressed)
        check_range(bytearray(new), bytearray(old))

    # create new archive
    arc = cab.CabArchive()
    arc.set_id = 0x0622

    # first example
    cff = cab.CabFile("hello.c")
    cff.contents = b'#include <stdio.h>\r\n\r\nvoid main(void)\r\n{\r\n    printf("Hello, world!\\n");\r\n}\r\n'
    cff.date = datetime.date(1997, 3, 12)
    cff.time = datetime.time(11, 13, 52)
    arc.add_file(cff)

    # second example
    cff = cab.CabFile("welcome.c")
    cff.contents = b'#include <stdio.h>\r\n\r\nvoid main(void)\r\n{\r\n    printf("Welcome!\\n");\r\n}\r\n\r\n'
    cff.date = datetime.date(1997, 3, 12)
    cff.time = datetime.time(11, 15, 14)
    arc.add_file(cff)

    # save file
    arc.save_file("/tmp/test.cab")

    # verify
    data = open("/tmp/test.cab", "rb").read()
    expected = (
        b"\x4D\x53\x43\x46\x00\x00\x00\x00\xFD\x00\x00\x00\x00\x00\x00\x00"
        b"\x2C\x00\x00\x00\x00\x00\x00\x00\x03\x01\x01\x00\x02\x00\x00\x00"
        b"\x22\x06\x00\x00\x5E\x00\x00\x00\x01\x00\x00\x00\x4D\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x6C\x22\xBA\x59\x20\x00\x68\x65\x6C\x6C"
        b"\x6F\x2E\x63\x00\x4A\x00\x00\x00\x4D\x00\x00\x00\x00\x00\x6C\x22"
        b"\xE7\x59\x20\x00\x77\x65\x6C\x63\x6F\x6D\x65\x2E\x63\x00\xBD\x5A"
        b"\xA6\x30\x97\x00\x97\x00\x23\x69\x6E\x63\x6C\x75\x64\x65\x20\x3C"
        b"\x73\x74\x64\x69\x6F\x2E\x68\x3E\x0D\x0A\x0D\x0A\x76\x6F\x69\x64"
        b"\x20\x6D\x61\x69\x6E\x28\x76\x6F\x69\x64\x29\x0D\x0A\x7B\x0D\x0A"
        b"\x20\x20\x20\x20\x70\x72\x69\x6E\x74\x66\x28\x22\x48\x65\x6C\x6C"
        b"\x6F\x2C\x20\x77\x6F\x72\x6C\x64\x21\x5C\x6E\x22\x29\x3B\x0D\x0A"
        b"\x7D\x0D\x0A\x23\x69\x6E\x63\x6C\x75\x64\x65\x20\x3C\x73\x74\x64"
        b"\x69\x6F\x2E\x68\x3E\x0D\x0A\x0D\x0A\x76\x6F\x69\x64\x20\x6D\x61"
        b"\x69\x6E\x28\x76\x6F\x69\x64\x29\x0D\x0A\x7B\x0D\x0A\x20\x20\x20"
        b"\x20\x70\x72\x69\x6E\x74\x66\x28\x22\x57\x65\x6C\x63\x6F\x6D\x65"
        b"\x21\x5C\x6E\x22\x29\x3B\x0D\x0A\x7D\x0D\x0A\x0D\x0A"
    )
    check_range(bytearray(data), bytearray(expected))

    # use cabextract to test validity
    argv = ["cabextract", "--test", "/tmp/test.cab"]
    rc = subprocess.call(argv)
    assert rc == 0

    # check we can parse what we just created
    arc = cab.CabArchive()
    arc.parse_file("/tmp/test.cab")

    # add an extra file
    arc.add_file(cab.CabFile("test.inf", b"$CHICAGO$"))

    # save with compression
    arc.save_file("/tmp/test.cab", True)

    # use cabextract to test validity
    check_archive("/tmp/test.cab")

    # open a folder with multiple folders
    for fn in ["data/multi-folder.cab", "data/ddf-fixed.cab"]:
        arc = cab.CabArchive()
        print("Parsing:", fn)
        old = open(fn, "rb").read()
        arc.parse(old)
        assert len(arc.files) == 2, len(arc.files)
        cff = arc.find_file("*.txt")
        assert cff.contents == b"test123", cff.contents

    # parse junk
    arc = cab.CabArchive()
    try:
        arc.parse_file("data/multi-folder-compressed.cab")
    except cab.NotSupportedError as e:
        pass


if __name__ == "__main__":
    main()
