#! /bin/bash

export EXIV2_PATH=/Users/min/Tools/exif/exiv2-0.25

function build_module
{
    python setup.py build
}

function build_myexiv2
{
    make
}

function clean
{
    make clean
    python setup.py clean
}

while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -c|clean)
            clean
            ;;
        -m|module)
            build_module
            ;;
        -e|myexiv2)
            build_myexiv2
            ;;
        *)
            build_module
            build_myexiv2
            ;;
    esac
    shift # past argument or value
done
