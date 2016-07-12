#include <cstdio>  
#include <cstring>  
#include <libexif/exif-data.h>
  
void read_exif_entry(ExifEntry *ee, void* ifd)  
{  
    char v[1024];  
//  strncpy(t, exif_tag_get_title_in_ifd(ee->tag, exif_entry_get_ifd(ee)), sizeof(t));  
//  strncpy(t, exif_tag_get_title_in_ifd(ee->tag, *((ExifIfd*)ifd)), sizeof(t));  
    //trim t  
    printf("%s: %s\n"  
//          , exif_tag_get_name_in_ifd(ee->tag, *((ExifIfd*)ifd))  
            , exif_tag_get_title_in_ifd(ee->tag, *((ExifIfd*)ifd))  
//          , exif_tag_get_description_in_ifd(ee->tag, *((ExifIfd*)ifd))  
            , exif_entry_get_value(ee, v, sizeof(v)));  
}  
  
void read_exif_content(ExifContent *ec, void *user_data)  
{  
    ExifIfd ifd = exif_content_get_ifd(ec);  
    if (ifd == EXIF_IFD_COUNT)  
        fprintf(stderr, "exif_content_get_ifd error");  
    printf("======IFD: %d %s======\n", ifd, exif_ifd_get_name(ifd));  
    exif_content_foreach_entry(ec, read_exif_entry, &ifd);  
}  
  
int main(int argc, char** argv)  
{  
    ExifData* ed = exif_data_new_from_file(argv[1]);  
    if (!ed) {  
        fprintf(stderr, "An error occur");  
        return 1;  
    }  
  
    //exif_data_set_option(ed,   
    exif_data_foreach_content(ed, read_exif_content, NULL);  
  
    exif_data_unref(ed);  
  
    return 0;  
}  
