import os

total_linecount = 0

def walk_folder(folder):
    global total_linecount
    # print('walking folder {}'.format(folder))
    for root, dirs, files in os.walk(folder):
        for filename in files:
            if not filename.endswith('.py'):
                continue
            with open(os.path.join(root, filename), 'r') as file:
                lines = file.readlines()
                lines = list(filter(lambda x: x.strip() != '', lines))
                file_linecount = len(lines)
                total_linecount += file_linecount
            # print('\t', f'reading file {filename}: {file_linecount}')
        for d in dirs:
            walk_folder(os.path.join(root, d))


if __name__ == '__main__':
    walk_folder('ldm')
    print('total linecount: {}'.format(total_linecount))

