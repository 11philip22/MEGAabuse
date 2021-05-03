FROM archlinux

RUN pacman -Sy automake make git autoconf libtool swig python3 glibc \
			   gcc python-setuptools python-pip curl c-ares openssl \
			   crypto++ zlib sqlite freeimage libsodium python-wheel --noconfirm
RUN git clone https://github.com/meganz/sdk.git

WORKDIR /sdk
RUN ./autogen.sh
RUN ./configure --disable-silent-rules --enable-python --disable-examples
RUN make
WORKDIR /sdk/bindings/python
RUN python setup.py bdist_wheel
