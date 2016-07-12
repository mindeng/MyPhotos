#include <stdio.h>
#include "exif.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>


const static int EXIF_BUF_LEN = 1024;
const static int READ_BUF_LEN = 10 * 1024;
static char exif_info[EXIF_BUF_LEN];
static char read_buf[READ_BUF_LEN];

static int format_json(char** buf, const char* k, const char* v, int* capacity, bool is_last = false)
{
    int n;
    if (is_last) {
	n = snprintf(*buf, *capacity, "\"%s\":\"%s\"", k, v);
    }
    else {
	n = snprintf(*buf, *capacity, "\"%s\":\"%s\",", k, v);
    }

    if (n < 0) {
	perror("myexif");
	abort();
    }

    *buf += n;
    *capacity -= n;
    
    return n;
}

static int format_json(char** buf, const char* k, int v, int* capacity, bool is_last = false)
{
    int n;
    if (is_last) {
	n = snprintf(*buf, *capacity, "\"%s\":%d", k, v);
    }
    else {
	n = snprintf(*buf, *capacity, "\"%s\":%d,", k, v);
    }

    if (n < 0) {
	perror("myexif");
	abort();
    }

    *buf += n;
    *capacity -= n;
    
    return n;
}

static int format_json(char** buf, const char* k, double v, int* capacity, bool is_last = false)
{
    int n;
    if (is_last) {
	n = snprintf(*buf, *capacity, "\"%s\":%f", k, v);
    }
    else {
	n = snprintf(*buf, *capacity, "\"%s\":%f,", k, v);
    }

    if (n < 0) {
	perror("myexif");
	abort();
    }

    *buf += n;
    *capacity -= n;
    
    return n;
}

// Return exif info as json string
const char* get_exif_info(const char* content, unsigned int size)
{
    easyexif::EXIFInfo result;
    char* buf = exif_info;
    int capacity = EXIF_BUF_LEN;
    int n;

    // Parse EXIF
    int code = result.parseFrom((unsigned char*)content, size);
    if (code != 0) {
	//printf("Error parsing EXIF: code %d\n", code);
	return NULL;
    }

    n = snprintf(buf, capacity, "{");
    buf += n;
    capacity -= n;

    format_json(&buf, "Make", result.Make.c_str(), &capacity);
    format_json(&buf, "Model", result.Model.c_str(), &capacity);
    format_json(&buf, "ImageWidth", (int)result.ImageWidth, &capacity);
    format_json(&buf, "ImageHeight", (int)result.ImageHeight, &capacity);
    
    // format_json(&buf, "ImageDescription",
    // 			result.ImageDescription.c_str(), &capacity);
    format_json(&buf, "DateTime", result.DateTime.c_str(), &capacity);
    format_json(&buf, "DateTimeOriginal",
			result.DateTimeOriginal.c_str(), &capacity);
    format_json(&buf, "DateTimeDigitized",
			result.DateTimeDigitized.c_str(), &capacity);
    format_json(&buf, "ExposureTime", result.ExposureTime, &capacity);
    format_json(&buf, "FNumber", result.FNumber, &capacity);
    format_json(&buf, "ISO", result.ISOSpeedRatings, &capacity);
    format_json(&buf, "FocalLengthIn35mmFormat",
		result.FocalLengthIn35mm, &capacity);

    format_json(&buf, "GPSLatitude", result.GeoLocation.Latitude,
		&capacity);
    format_json(&buf, "GPSLongitude", result.GeoLocation.Longitude,
		&capacity);
    format_json(&buf, "GPSAltitude", result.GeoLocation.Altitude,
		&capacity, true);
    snprintf(buf, capacity, "}");

    return exif_info;
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

const char* get_exif_info(const char* path)
{
    const char* exif_info = NULL;
    unsigned int size = 0;
    char *buf = map_file(path, &size);
    
    if (buf != NULL) {
	exif_info = get_exif_info(buf, size);
	unmap_file(buf, size);
    }

    return exif_info;
}

const char* quick_read(const char* path, unsigned int offset,
		       unsigned int size)
{
    unsigned int total_size = 0;
    char *buf = map_file(path, &total_size);
    
    if (buf != NULL) {
	size = size <= READ_BUF_LEN ? size : READ_BUF_LEN;
	if (size < READ_BUF_LEN) {
	    memset(read_buf, 0, READ_BUF_LEN);
	}
	memcpy(read_buf, buf + offset, size);
	unmap_file(buf, total_size);
    }

    return read_buf;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
	printf("Usage: demo <JPEG file>\n");
	return -1;
    }

    printf("%s\n", get_exif_info(argv[1]));

    return 0;
}
