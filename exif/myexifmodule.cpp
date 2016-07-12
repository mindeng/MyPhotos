#include <Python.h>

extern const char* get_exif_info(const char* path);
extern const char* quick_read(const char* path, unsigned int offset,
			      unsigned int size);

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

static PyObject *
myexif_quick_read(PyObject *self, PyObject *args)
{
    const char *path;
    unsigned int offset;
    unsigned int size;
    const char* content;

    if (!PyArg_ParseTuple(args, "sII", &path, &offset, &size))
        return NULL;

    content = quick_read(path, offset, size);
    
    return Py_BuildValue("s#", content, size);
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
    "quick_read",
    (PyCFunction)myexif_quick_read,
    METH_VARARGS | METH_KEYWORDS,
    "Using mmap to read file."
  },

  
  {NULL, NULL, 0, NULL}   /* sentinel */
};


PyMODINIT_FUNC
initmyexif(void)
{
    (void) Py_InitModule("myexif", myexif_methods);
}
