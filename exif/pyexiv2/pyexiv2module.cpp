#include <Python.h>
#include <string>

// For md5
#include <cstdio>
#include <cstdlib>
#include <cstring>
#if defined(__APPLE__)
#  define COMMON_DIGEST_FOR_OPENSSL
#  include <CommonCrypto/CommonDigest.h>
#  define SHA1 CC_SHA1
#else
#  include <openssl/md5.h>
#endif

// For mmap
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>

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


extern const std::string get_exif_info(const char* path);

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

static char* map_file(const char* path, unsigned int* size)
{
    int fd;
    struct stat sb;  
    char *mapped;
  
    /* 打开文件 */  
    if ((fd = open(path, O_RDONLY)) < 0) {  
        perror("open");
	return NULL;
    }  
  
    /* 获取文件的属性 */  
    if ((fstat(fd, &sb)) == -1) {  
        perror("fstat");
	return NULL;
    }  
  
    /* 将文件映射至进程的地址空间 */  
    if ((mapped = (char *)mmap(NULL,
			       sb.st_size,
			       PROT_READ,
			       MAP_SHARED,
			       fd,
			       0)) == (void *)-1) {  
        perror("mmap");
	return NULL;
    }  
  
    /* 映射完后, 关闭文件也可以操纵内存 */  
    close(fd);  

    *size = sb.st_size;

    return mapped;
}

static void unmap_file(char *mapped, unsigned int size)
{
    /* 释放存储映射区 */  
    if ((munmap((void *)mapped, size)) == -1) {  
        perror("munmap");  
    }  
}

static void md5_update(MD5_CTX& c, const char* data, int length)
{
    while (length > 0) {
        if (length > 512) {
            MD5_Update(&c, data, 512);
        } else {
            MD5_Update(&c, data, length);
        }
        length -= 512;
        data += 512;
    }
}

// If file size is equal or samller than 3 * 32KB, than calculate md5 for the whole file
// Otherwise calculate md5 for the first, middle and last 32KB bytes.
static void calc_middle_md5(const char* path, unsigned char* out)
{
    const int CHUNK_SIZE = 32 * 1024;
    const int CHUNK_NUM = 3;

    unsigned int total_size = 0;
    char *buf = map_file(path, &total_size);
    
    if (buf != NULL) {
        MD5_CTX c;
        const int size = CHUNK_SIZE;
        const char* data = buf;

        MD5_Init(&c);

        if (total_size <= CHUNK_NUM * CHUNK_SIZE) {
            // calc for the whole file
            md5_update(c, data, total_size);
        }
        else {
            // chunk 1
            md5_update(c, data, size);

            // chunk 2
            data = buf + (total_size - size) / 2;
            md5_update(c, data, size);

            // chunk 3
            data = buf + total_size - size;
            md5_update(c, data, size);
        }

        MD5_Final(out, &c);
        unmap_file(buf, total_size);
    }
}

static PyObject *
myexif_cp_file(PyObject *self, PyObject *args)
{
    const char *src;
    const char *dst;

    if (!PyArg_ParseTuple(args, "ss", &src, &dst))
        return NULL;

    int ret = cp_file(src, dst);
    
    return Py_BuildValue("i", ret);
}

static PyObject *
myexif_calc_middle_md5(PyObject *self, PyObject *args)
{
    const char *path;
    const int DIGEST_LEN = 16;
    unsigned char digest[DIGEST_LEN];

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    calc_middle_md5(path, digest);
    
    return Py_BuildValue("s#", digest, DIGEST_LEN);
}

static PyObject *
myexif_get_exif_info(PyObject *self, PyObject *args)
{
    const char *path;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    std::string exif_info = get_exif_info(path);
    
    return Py_BuildValue("s", exif_info.c_str());
}

static PyMethodDef myexif_methods[] = {
    /* The cast of the function is necessary since PyCFunction values
     * only take two PyObject* parameters, and keywdarg_parrot() takes
     * three.
     */
  {
    "get_exif_info",
    (PyCFunction)myexif_get_exif_info,
    METH_VARARGS | METH_KEYWORDS,
    "Get exif info as json object."
  },

  {
      "calc_middle_md5",
      (PyCFunction)myexif_calc_middle_md5,
      METH_VARARGS | METH_KEYWORDS,
      "Calculate md5 for file."
  },

  {
    "cp_file",
    (PyCFunction)myexif_cp_file,
    METH_VARARGS | METH_KEYWORDS,
    "Copy file."
  },

  
  {NULL, NULL, 0, NULL}   /* sentinel */
};

PyMODINIT_FUNC
initmyexif(void)
{
    (void) Py_InitModule("myexif", myexif_methods);
}
