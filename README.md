照片、视频打包工具
===================

为方便打包备份照片、视频等个人多媒体文件，编写了该自动化打包工具。


工具特点
--------

工具特点如下：
* 读取照片视频等文件中的 exif ，以取得该文件的真实拍摄日期（如文件不包含真实拍摄信息，则使用文件的 ctime 时间）
* 按时间排序，并根据参数指定的包大小将文件按顺序归档（实际产出的包大小并非十分精确，可能会比指定的大小略大）
* 维护一个已归档文件的 md5 数据库，以便增量归档（下次归档时，重复文件会被忽略）
* 数据库中同时会按路径缓存文件的 md5 值，方便下次归档同一个文件夹时，不需要再全部重新计算一遍 md5 （为增量归档提速）。为防止缓存的文件路径失效，可指定 --ignore-prefix 参数，忽略可能变化的路径前缀（适用于备份数据源存放在U盘、移动硬盘等情况）
* 采用 AES 算法加密归档文件，AES 密钥随机生成，并加密保存在数据库中，需要用户口令才能解密密钥，进而解密归档文件
* 支持设置临时工作路径，减少磁盘I/O，加速打包过程（例如将 tmpfs/ramdisk 路径设置为工作路径）
* 密码防错功能，在第一次打包时输入密码后，后续打包强制要求使用同一个密码，以防止不小心使用了不同密码，导致后续密码混乱，无法解包
* 支持打包、解密两种模式（后续将解密模式优化成解包模式）
* 归档过程可随时中断，下次重新运行即可

另外，里面的几个小工具也可以单独使用，例如 get_exif.py, enc_file.py 。

enc_file.py 除了可以加密、解密文件，还支持加密、解密字符串（输出也是字符串，加密并base64处理），方便使用。


依赖安装
--------

* Python 2.7 （2.6没测试过，应该没问题，有问题请反馈给我）。
* pycrypto
* PIL
* hachoir_metadata

参考安装步骤
+++++++++++++

如果是 OS X 系统，建议使用 Homebrew 重新安装 Python，否则部分依赖可能安装失败（也可以先尝试不重装 Python，如果遇到安装依赖包失败时再重装 Python）：

```
$ brew reinstall python
```

如果没装 pip，先安装 pip：

```
$ wget https://bootstrap.pypa.io/get-pip.py -P /tmp && sudo -H python /tmp/get-pip.py
```

安装 Python 依赖包（视你的 Python 环境而定，可能需要 root 权限。Homebrew 安装的 Python 不需要 root）：

```
$ pip install PIL --allow-external PIL --allow-unverified PIL
$ pip install hachoir-core hachoir-parser hachoir-metadata
```

详细用法
--------

详细用法请参考命令行帮助文档：

```
$ ./pack_photos.py -h
usage: pack_photos.py [-h] [-o OUTPUT] [--db DB_PATH]
[--ignore-prefix IGNORE_PREFIX] [-p PASSWORD]
[--no-encrypt NO_ENCRYPT] [--tmp TMP]
[--exclude-dir EXCLUDE_DIR] [-d]
src

Pack photos for backup.

positional arguments:
src                   Source path or directory. In pack mode(default), this
specify the photos/videos directory which will be
packed; in decrypt mode(-d), this specify the archive
file which will be decrypted.

optional arguments:
-h, --help            show this help message and exit
-o OUTPUT, --output OUTPUT   
Output directory or path. In pack mode(default), this
specify the output directory of encrypted archives; in
decrypt mode(-d), this specify the output path or
directory for the decrypted archive file.
--db DB_PATH          Database file path
--ignore-prefix IGNORE_PREFIX
Ignore the specified path prefix when caching md5
-p PASSWORD, --password PASSWORD
Password to encrypt the AES key
--no-encrypt NO_ENCRYPT
No need to encrypt the archive files
--tmp TMP             Temporary working directory
--exclude-dir EXCLUDE_DIR
Excldue directory
-d, --decrypt         Decrypt the specified archive file.
```

