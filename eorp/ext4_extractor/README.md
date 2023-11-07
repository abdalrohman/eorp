# Ext4 Extractor

This repository contains a Python tool for extracting information and files from Android Ext4 filesystem images. It includes two main classes: `ReadExt4` and `ExtractExt4`, each in their own Python files.

## ReadExt4 Class

The `ReadExt4` class, located in `ext4_info.py`, reads and processes Ext4 filesystems, extracting various information such as file contexts, configurations, and filesystem features.

### Usage

To use the `ReadExt4` class, provide the paths to the Ext4 image file and the output directory for info files as command-line arguments when running the script:

```bash
python ext4_info.py /path/to/image.ext4 /path/to/output/directory/
```

This command will extract information from the Ext4 image at `/path/to/image.ext4` and save it in the directory at `/path/to/output/directory/`. Make sure to replace these paths with the actual paths on your system.

## ExtractExt4 Class

The `ExtractExt4` class, located in `extract_ext4.py`, extracts files from an Ext4 filesystem. It takes an image file path and an output directory path as arguments, and copies files from the image to the output directory.

### Usage

To use the `ExtractExt4` class, provide the paths to the Ext4 image file and the output directory as command-line arguments when running the script:

```bash
python extract_ext4.py /path/to/image.ext4 /path/to/output/directory/
```

This command will extract files from the Ext4 image at `/path/to/image.ext4` and save them in the directory at `/path/to/output/directory/`. Make sure to replace these paths with the actual paths on your system.

## Integration with Other Projects

You can use these classes in your own Python projects by importing them:

```python
from ext4_info import ReadExt4
from extract_ext4 import ExtractExt4
```

Then, you can create instances of these classes and call their methods as needed. For example:

```python
reader = ReadExt4(image_path, info_path)
reader.read_ext4()

extractor = ExtractExt4(image_path, out_path)
extractor.extract_files()
```

This tool is particularly useful for Android ROM developers or anyone who needs to extract system files from an Android device. Happy coding! 😊
