#include <stdio.h>

#ifdef _WIN32
   //define something for Windows (32-bit and 64-bit, this part is common)
   #ifdef _WIN64
      //define something for Windows (64-bit only)
   #endif
#elif __APPLE__
#include <copyfile.h>
#elif __linux__
    // linux

// For sendfile
#include <iostream>
#include <sys/sendfile.h>  // sendfile
#include <fcntl.h>         // open
#include <unistd.h>        // close
#include <sys/stat.h>      // fstat
#include <sys/types.h>     // fstat
#include <ctime>

#elif __unix__ // all unices not caught above
    // Unix
#elif defined(_POSIX_VERSION)
    // POSIX
#else
#   error "Unknown compiler"
#endif


#if defined(__APPLE__)
int cp_file(const char *src, const char *dst)
{
    /* Initialize a state variable */
    copyfile_state_t s;
    int ret = 0;

    s = copyfile_state_alloc();
    /* Copy the data and extended attributes of one file to another */
    ret = copyfile(src, dst, s, COPYFILE_DATA | COPYFILE_STAT | COPYFILE_EXCL);
    /* Release the state variable */
    copyfile_state_free(s);

    if (ret != 0) {
        perror("cp_file");
    }

    return ret;
}
#elif __linux__
int cp_file(const char *src, const char *dst)
{
    struct stat stat_source;
    int source = open(src, O_RDONLY, 0);
    int dest = open(dst, O_WRONLY | O_CREAT | O_EXCL, 0644);

    // struct required, rationale: function stat() exists also
    fstat(source, &stat_source);
    sendfile(dest, source, 0, stat_source.st_size);

    close(source);
    close(dest);

    return 0;
}
#endif

int main(int argc, char** argv)
{
    const char* src = argv[1];
    const char* dst = argv[2];
    return cp_file(src, dst);
}
