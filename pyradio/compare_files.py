import hashlib

class CompareFiles(object):
    ''' Class to compare two files  by content '''

    def __init__(self, fname1, fname2):
        ''' Just provide two files' pathname and use equal of different
            properties to get the result.
            They return True or False, or None if an error opening any
            one of the files occurs.
        '''

        self.fname1 = fname1
        self.fname2 = fname2
        self.sha1 = None
        self.sha2 = None

    @property
    def equal(self):
        ''' Checks if files are equal
            Returns
                True    files are equal
                False   files are different
                None    error reading files
        '''
        if self._compare_files():
            return True if self.sha1 == self.sha2 else False
        else:
            return None

    @equal.setter
    def equal(self, val):
        raise ValueError('This property is read-only')

    @property
    def different(self):
        ''' Checks if files are different
            Returns
                True    files are different
                False   files are equal
                None    error reading files
        '''
        if self._compare_files():
            return False if self.sha1 == self.sha2 else True
        else:
            return None

    @different.setter
    def different(self, val):
        raise ValueError('This property is read-only')

    def _compare_files(self):
        try:
            self.sha1 = self._sha512(self.fname1)
            self.sha2 = self._sha512(self.fname2)
            return True
        except:
            self.sha1 = None
            self.sha2 = None
            return False

    def _sha512(self, fname):
        hash_sha512 = hashlib.sha512()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha512.update(chunk)
                return hash_sha512.hexdigest()

if __name__ == '__main__':
    cmp = CompareFiles('/home/spiros/.bashrc',
                       '/home/spiros/.zshrc')

    res = cmp.different
    if res is None:
        print('Error opening files')
    else:
        if res:
            print('Files are different')
        else:
            print('Files are equal')

