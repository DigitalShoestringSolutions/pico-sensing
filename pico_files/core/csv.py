# Save data to a local csv file

import os # for checking file size
#from core.timestamp import get_timestamp # ISO8601 timestrings

def save(data:dict, filename:str="data.csv", add_timestamp=True, max_size:int=1000000):
    """Receives a dictionary and writes this data to CSV.

    Beware dictionaries are not ordered in micropython, so CSV columns may not be in the order expected.

    :param dict data:          Data to save to CSV file. The dictionary keys are used as column headers.
    :param str filename:       (optional) The file to add the data to. Defaults to "data.csv"
    :param bool add_timestamp: (optional) Add an ISO8601 timestamp to the data. Defaults to True. Will not overwrite an existing key `timestamp` if present in `data`.
    :param in max_size:        (optional) Max file size in bytes. After this no new data will be written. Default is is 1MB to fit within Pico's total 2MB budget.
    
    """
    print(f"saving data {data}")
    
    # Get timestamp asap, even if not used
    #timestamp = get_timestamp()


    filesize = _filesize(filename)
    if filesize < max_size:
        
        # Add timestamp
        #if add_timestamp:
        #    data = data | {"timestamp" : timestamp}

        # Read existing CSV headers
        headers = _read_headers(filename)

        # Add data to existing columns where suitable headers exist
        data_line = []
        for h in headers:
            if h in data: # str as read from file
                #print(f"adding data {data[h]} to existing header {h}")
                print(f"{data[h]} -> {h}")
                data_line.append(str(data[h]))
            else:
                data_line.append('') # add empty string to list for commas to fill early cols that no longer have data

        # Add data to new columns
        header_rewrite_needed = False
        for k,v in data.items():      # iterates through data, unlike previous para which went through headers
            if str(k) not in headers: # if it is in headers, will have been dealt with in previous paragraph
                header_rewrite_needed = True
                print(f"appending new col {k} with data {v}")
                headers.append(str(k))
                data_line.append(str(v))

        # write new headers if needed
        if header_rewrite_needed:
            _rewrite_headers(headers, filename)


        # append data
        print(f"writing data line {data_line}")
        with open(filename, "at") as f:
            f.write(','.join(data_line) + '\n') # leave a trailing newline at EoF

    else:
        print(f"ERROR: data not saved to CSV due to filesize at limit {filesize}") # don't bother with proper logging on an MCU. Especially when the message is no room to log!


def _filesize(filename) -> int:
    """Get the size of a file in bytes"""
    #Open file and close it again to ensure it exists. There are probably a few more efficient ways to do this.
    with open(filename, 'at') as f: # append mode
        pass
    filesize = os.stat(filename)[6]           # File size in bytes
    #print(f"filesize is {filesize}")
    return filesize


def _read_headers(filename) -> list:
    """Read the first line of a CSV file"""
    with open(filename, 'r') as f:
        headerline = f.readline().strip('\n\r')
    #print(f"headerline read as {headerline}")
    headers = headerline.split(',') # ordered list
    if '' in headers: # trailing comma or empty file means empty string makes it into the list
        headers.remove('')
        pass
    #print(f"headers are {headers} length {len(headers)}")
    print(f"headers {headers}")
    return headers


def _rewrite_headers(new_headers: list, filename: str = "data.csv", buff_size: int = 3) -> None:
    """Add more columns to an existing CSV file. Assumes that new_headers starts exactly as the old headers did."""
    # filename etc could be passed to this as a class. But I'd rather the usage simplicity of not having to init, as there is only one external function
    print(f"writing replacemnet headers {new_headers}")

    # Problem here. 'Inserting' new headers at the start of the file overwrites the first few bytes of the file. It does not stop overwriting at the first \n encountered.
    # The new headers will be longer than the old, hence the first line (or more) of old data gets mangled, partially lost.
    # So, a new goal: find a memory efficient way of replacing the headers with no data loss that remains a valid CSV.

        # Option 0: Pad the headers line to take plenty of bytes, so it can be rewritten at constant length? ugly.
        # Option 1: read the whole file into memory, navigate to start of file, write new headers, write all data? limits file size to RAM, risky data loss if process interrupted
        # Option 2: Write new headers to alternative file, iterate over old file and new copying data, add new data, delete original file, rename alt to primary? Low ram requirement but limits file size to half storage
        # Option 3: Working on a single file, read a couple of lines into a buffer and FIFO across the file moving everything along chunk by chunk? Resource efficient but hard to f.seak() 

    # Attempt Option 3 (the best but hardest):
    with open(filename, "r") as readfile:
        with open(filename, "r+") as writefile:  # open the same file twice in separate instances with separate seek points

            # pre-load line buffer
            line_buffer = []
            readfile.seek(0)
            old_headers = readfile.readline() # discard old headers
            for _ in range(buff_size):  # read enough lines of data to certainly cover what might get overwritten by new headers
                line_buffer.append(readfile.readline())  # if eof is hit before buff_size, empty strings will be appended to the list. This is ok.
            print(f"preloaded line_buffer with {line_buffer}")  # list of strings including \n at end of each

            # Write new headers
            writefile.seek(0)  # maintains a separate seek pointer to readfile, despite being the same file.
            writefile.write(','.join(new_headers) + '\n')

            # Copy data across
            while len(line_buffer) > 0:
                readline = readfile.readline()
                if readline != '':  # if not at eof
                    line_buffer.append(readline)

                writefile.write(line_buffer.pop(0))

    print("header rewrite complete")



# test
if __name__ == '__main__':
    save({'varA': "a0"})             # mvp
    save({'varA':"a1",'varB':"b1"})  # new header, rewrite
    save({'varA':"a2"})              # missing last header
    save({'varB':"b3"})              # missing early header
    save({'varA':"a4",'varB':"b4"})  # back to normal
    # So far file is 6 lines:
    """varA,varB
    a0
    a1,b1
    a2,
    ,b3
    a4,b4
    """
    # Now let's make it harder
    save({'varC':"c5", 'varD':"d5"}) # two new headers at once, nothing in common with old
    save({'varA':"a6", 'varD':"d6"}) # missing middle headers
    # Final file is:
    """varA,varB,varD,varC
    a0
    a1,b1
    a2,
    ,b3
    a4,b4
    ,,d5,c5
    a6,,d6,
    """
    # perfect.