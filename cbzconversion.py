import os
import xml.etree.ElementTree as ET
import shutil
import re
import zipfile

def extract_author_and_clean_title(folder_name):
    """
    Extracts the author and title from a folder name using a regex pattern.
    Assumes folder name is in the format: [Author] Title or (Author) Title.
    """
    match = re.match(r'^[\[\(](.*?)[\]\)] ?(.*)', folder_name)
    if match:
        author = match.group(1).strip()  # Extract author or group
        title = match.group(2).strip()   # Extract the rest (title)
        return author, title
    return None, folder_name  # No match found, return folder name as title

def process_manga(input_path, output_folder, callback=None):
    """
    Processes a single manga folder to generate ComicInfo.xml and CBZ files.
    Arguments:
        input_path (str): Path to the folder containing the manga images.
        output_folder (str): Path to the folder where processed files will be stored.
        callback (function): Optional callback function to indicate when processing is complete.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Error: Input path does not exist: {input_path}")

    # Extract folder name from the provided path
    folder_name = os.path.basename(os.path.normpath(input_path))

    # Extract author and title from folder name
    author, cleaned_title = extract_author_and_clean_title(folder_name)

    # Create output directory for the processed files
    new_dir_path = os.path.join(output_folder, folder_name)
    if not os.path.exists(new_dir_path):
        os.makedirs(new_dir_path)

    # CBZ file path
    cbz_filename = os.path.join(new_dir_path, f"{cleaned_title}.cbz")

    # Skip processing if CBZ already exists
    if os.path.exists(cbz_filename):
        print(f"Skipping {folder_name}: CBZ file already exists ({cbz_filename}).")
        return

    # Generate ComicInfo.xml
    comic_info = ET.Element("ComicInfo")
    title_element = ET.SubElement(comic_info, "Title")
    title_element.text = cleaned_title

    if author:
        author_element = ET.SubElement(comic_info, "Author")
        author_element.text = author
        print(f"Extracted author: {author}")

    # Save ComicInfo.xml
    comic_info_path = os.path.join(new_dir_path, "ComicInfo.xml")
    tree = ET.ElementTree(comic_info)
    with open(comic_info_path, "wb") as file:
        tree.write(file, encoding="utf-8", xml_declaration=True)
        print(f"Written ComicInfo.xml for {cleaned_title}.")

    # Search for the cover image
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
    file_name_variations = ['1', '01', '001', '0001']
    found = False
    for filename_base in file_name_variations:
        for ext in image_extensions:
            image_file = os.path.join(input_path, f"{filename_base}{ext}")
            if os.path.exists(image_file):
                new_file_name = f"cover{ext}"
                new_file_path = os.path.join(new_dir_path, new_file_name)
                shutil.copy(image_file, new_file_path)
                print(f"Copied and renamed {image_file} to {new_file_path} as cover image.")
                found = True
                break
        if found:
            break

    # Collect all image files for CBZ creation (excluding ComicInfo.xml and cover)
    image_files = [f for f in os.listdir(input_path) if f.lower().endswith(image_extensions)]
    image_files.sort()  # Sort image files to maintain correct order in CBZ

    if image_files:
        # Create the CBZ file
        print(f"Creating CBZ for {cleaned_title}...")
        try:
            with zipfile.ZipFile(cbz_filename, 'w') as cbz:
                # Add all image files to CBZ
                for image_file in image_files:
                    image_path = os.path.join(input_path, image_file)
                    cbz.write(image_path, arcname=image_file)
                print(f"CBZ file created: {cbz_filename}")
        except Exception as e:
            print(f"Error creating CBZ file: {e}")
    else:
        print(f"No image files found in {folder_name}")

    # Notify via callback if provided
    if callback:
        callback()

def convert_cbz(input_path, output_path, on_complete=None):
    """
    Public function to process a single manga folder into a CBZ file.
    Arguments:
        input_path (str): Path to the input directory.
        output_path (str): Path to the output directory.
        on_complete (function): Optional callback function to indicate completion.
    """
    print("Starting CBZ conversion...")
    try:
        process_manga(input_path, output_path, callback=on_complete)
    except Exception as e:
        print(f"An error occurred: {e}")
    else:
        print("CBZ conversion completed successfully.")
