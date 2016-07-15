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

extern const std::string get_exif_info(const char* path);

static void md5(const char* data, int length, unsigned char out[16]) {
    MD5_CTX c;

    MD5_Init(&c);

    while (length > 0) {
        if (length > 512) {
            MD5_Update(&c, data, 512);
        } else {
            MD5_Update(&c, data, length);
        }
        length -= 512;
        data += 512;
    }

    MD5_Final(out, &c);
}

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


static void quick_read(const char* path, unsigned int offset,
		       unsigned int size, char* out)
{
    unsigned int total_size = 0;
    char *buf = map_file(path, &total_size);
    
    if (buf != NULL) {
	memcpy(out, buf + offset, size);
	unmap_file(buf, total_size);
    }
}

static PyObject *
myexif_calc_file_md5(PyObject *self, PyObject *args)
{
    const char *path;
    unsigned int offset;
    unsigned int size;
    char* data;
    const int DIGEST_LEN = 16;
    unsigned char digest[DIGEST_LEN];

    if (!PyArg_ParseTuple(args, "sII", &path, &offset, &size))
        return NULL;

    if (size <= 0 || size > 10 * 1024 * 1024) {
	return NULL;
    }

    data = new char[size];
    quick_read(path, offset, size, data);
    md5(data, size, digest);
    delete[] data;
    
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
      "calc_file_md5",
      (PyCFunction)myexif_calc_file_md5,
      METH_VARARGS | METH_KEYWORDS,
      "Calculate md5 for file."
  },

  
  {NULL, NULL, 0, NULL}   /* sentinel */
};

PyMODINIT_FUNC
initmyexif(void)
{
    (void) Py_InitModule("myexif", myexif_methods);
}
