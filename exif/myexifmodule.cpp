#include <Python.h>

extern const char* get_exif_info(const char* path);
extern void quick_read(const char* path, unsigned int offset,
		       unsigned int size, char* out);
extern void md5(const char* data, int length, unsigned char out[16]);

static PyObject *
myexif_calc_md5_for_file(PyObject *self, PyObject *args)
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
    const char* exif_info;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    exif_info = get_exif_info(path);
    
    return Py_BuildValue("s", exif_info);
}

/* static PyObject * */
/* myexif_exec_demo(PyObject *self, PyObject *args) */
/* { */
/*     const char *path; */
/*     int sts; */

/*     if (!PyArg_ParseTuple(args, "s", &path)) */
/*         return NULL; */
/*     char command[512] = "/Users/min/Tools/exif/easyexif-master/demo "; */
/*     strncpy(command+strlen(command), path, 256); */
/*     sts = system(command); */
/*     return Py_BuildValue("i", sts); */
/* } */

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
      "calc_md5_for_file",
      (PyCFunction)myexif_calc_md5_for_file,
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
