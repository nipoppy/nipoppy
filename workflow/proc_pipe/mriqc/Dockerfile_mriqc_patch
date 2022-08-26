FROM ubuntu

RUN set -xe && echo '#!/bin/sh' > /usr/sbin/policy-rc.d && echo 'exit 101' >> /usr/sbin/policy-rc.d && chmod +x /usr/sbin/policy-rc.d && dpkg-divert --local --rename --add /sbin/initctl && cp -a /usr/sbin/policy-rc.d /sbin/initctl && sed -i 's/^exit.*/exit 0/' /sbin/initctl && echo 'force-unsafe-io' > /etc/dpkg/dpkg.cfg.d/docker-apt-speedup && echo 'DPkg::Post-Invoke { "rm -f /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/*.deb /var/cache/apt/*.bin || true"; };' > /etc/apt/apt.conf.d/docker-clean && echo 'APT::Update::Post-Invoke { "rm -f /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/*.deb /var/cache/apt/*.bin || true"; };' >> /etc/apt/apt.conf.d/docker-clean && echo 'Dir::Cache::pkgcache ""; Dir::Cache::srcpkgcache "";' >> /etc/apt/apt.conf.d/docker-clean && echo 'Acquire::Languages "none";' > /etc/apt/apt.conf.d/docker-no-languages && echo 'Acquire::GzipIndexes "true"; Acquire::CompressionTypes::Order:: "gz";' > /etc/apt/apt.conf.d/docker-gzip-indexes && echo 'Apt::AutoRemove::SuggestsImportant "false";' > /etc/apt/apt.conf.d/docker-autoremove-suggests

RUN [ -z "$(apt-get indextargets)" ]

RUN mkdir -p /run/systemd && echo 'docker' > /run/systemd/container

CMD ["/bin/bash"]

RUN echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/90circleci   && echo 'DPkg::Options "--force-confnew";' >> /etc/apt/apt.conf.d/90circleci

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends apt-utils autoconf build-essential bzip2 ca-certificates libtool locales lsb-release pkg-config unzip wget xvfb && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN locale-gen en_US.UTF-8 || true

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

ENV CONDA_PATH=/opt/conda

ARG CONDA_VERSION=py38_4.10.3

ARG SHA256SUM=935d72deb16e42739d69644977290395561b7a6db059b316958d97939e9bdf3d

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-x86_64.sh -O miniconda.sh && echo "${SHA256SUM}  miniconda.sh" > miniconda.sha256 && sha256sum -c --status miniconda.sha256 && mkdir -p /opt && sh miniconda.sh -b -p ${CONDA_PATH} && rm miniconda.sh miniconda.sha256 && ln -s ${CONDA_PATH}/etc/profile.d/conda.sh /etc/profile.d/conda.sh && echo ". ${CONDA_PATH}/etc/profile.d/conda.sh" >> ~/.bashrc && echo "conda activate base" >> ~/.bashrc && find ${CONDA_PATH}/ -follow -type f -name '*.a' -delete && find ${CONDA_PATH}/ -follow -type f -name '*.js.map' -delete && ${CONDA_PATH}/bin/conda clean -afy


ENV PATH=/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin CPATH=/opt/conda/include: PYTHONNOUSERSITE=1


RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda python=3.8 attrs=21.2 codecov=2.1 colorclass coverage=6.0 curl datalad=0.15
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda dipy=1.4 
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda flake8 
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda git git-annex=*=alldep* graphviz=2.49 h5py=3.2 indexed_gzip=1.6 jinja2=2.11 libxml2=2.9 libxslt=1.1 lockfile=0.12 "matplotlib>=3.3,<4" 
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda mkl=2021.3 mkl-service=2.4 nibabel=3.2 nilearn=0.8 nipype=1.6 nitime=0.9 nodejs=16 numpy=1.20 packaging=21 pandas=1.2 
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda pandoc=2.14 pbr pip=21.3 pockets psutil=5.8 pydot=1.4 pydotplus=2.0 pytest=6.2 pytest-cov=3.0 pytest-env=0.6 pytest-xdist pyyaml=5.4 requests=2.26 
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda scikit-image=0.19 scikit-learn=0.24 scipy=1.6 seaborn=0.11 setuptools=58.2 sphinx=4.2 sphinx_rtd_theme=1.0 "svgutils>=0.3.4,<0.4" toml=0.10 
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda traits=6.2 zlib=1.2 zstd=1.5; sync && chmod -R a+rX ${CONDA_PATH}; sync && chmod +x ${CONDA_PATH}/bin/*; sync && ${CONDA_PATH}/bin/conda clean -afy && sync && rm -rf ~/.conda ~/.cache/pip/*; sync

RUN ${CONDA_PATH}/bin/python -c "from matplotlib import font_manager" && sed -i 's/\(backend *: \).*$/\1Agg/g' $( ${CONDA_PATH}/bin/python -c "import matplotlib; print(matplotlib.matplotlib_fname())" )

RUN ${CONDA_PATH}/bin/python -m pip install --no-cache-dir -U etelemetry nitransforms templateflow transforms3d

RUN ${CONDA_PATH}/bin/npm install -g svgo@^2.3 bids-validator@1.8.0 && rm -rf ~/.npm ~/.empty /root/.npm

ENV LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${CONDA_PATH}/lib"

# Install AFNI latest (neurodocker build)
ENV AFNI_DIR="/opt/afni"
RUN echo "Downloading AFNI ..." \
    && mkdir -p ${AFNI_DIR} \
    && curl -fsSL --retry 5 https://afni.nimh.nih.gov/pub/dist/tgz/linux_openmp_64.tgz \
    | tar -xz -C ${AFNI_DIR} --strip-components 1

ENV PATH=/opt/afni:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin AFNI_IMSAVE_WARNINGS=NO AFNI_MODELPATH=/opt/afni/models AFNI_TTATLAS_DATASET=/opt/afni/atlases AFNI_PLUGINPATH=/opt/afni/plugins

#ENV PATH="${AFNI_DIR}:$PATH" \
#    AFNI_IMSAVE_WARNINGS="NO" \
#    AFNI_MODELPATH="${AFNI_DIR}/models" \
#    AFNI_TTATLAS_DATASET="${AFNI_DIR}/atlases" \
#    AFNI_PLUGINPATH="${AFNI_DIR}/plugins"
    
# Install AFNI's dependencies
RUN ${CONDA_PATH}/bin/conda install -c conda-forge -c anaconda \
                            gsl                                \
                            xorg-libxp                         \
                            scipy=1.8                          \
    && ${CONDA_PATH}/bin/conda install -c sssdgc png \
    && sync \
    && ${CONDA_PATH}/bin/conda clean -afy; sync \
    && rm -rf ~/.conda ~/.cache/pip/*; sync \
    && ln -s ${CONDA_PATH}/lib/libgsl.so.25 /usr/lib/x86_64-linux-gnu/libgsl.so.19 \
    && ln -s ${CONDA_PATH}/lib/libgsl.so.25 /usr/lib/x86_64-linux-gnu/libgsl.so.0 \
    && ldconfig
    
RUN apt-get update \
 && apt-get install -y -q --no-install-recommends     \
                    libcurl4-openssl-dev              \
                    libgdal-dev                       \
                    libgfortran-8-dev                 \
                    libgfortran4                      \
                    libglw1-mesa                      \
                    libgomp1                          \
                    libjpeg62                         \
                    libnode-dev                       \
                    libssl-dev                        \
                    libudunits2-dev                   \
                    libxm4                            \
                    libxml2-dev                       \
                    netpbm                            \
                    tcsh                              \
                    xfonts-base                       \
 && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
 && ldconfig
 
# Installing ANTs 2.3.4 (NeuroDocker build)
ENV ANTSPATH="/opt/ants"
WORKDIR $ANTSPATH
RUN curl -sSL "https://dl.dropbox.com/s/gwf51ykkk5bifyj/ants-Linux-centos6_x86_64-v2.3.4.tar.gz" \
    | tar -xzC $ANTSPATH --strip-components 1
#ENV PATH="$ANTSPATH:$PATH"
ENV PATH=/opt/ants:/opt/afni:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Install FSL 5.0.11
RUN curl -sSL https://fsl.fmrib.ox.ac.uk/fsldownloads/fsl-5.0.11-centos7_64.tar.gz | tar zxv --no-same-owner -C /opt \
    --exclude='fsl/doc' \
    --exclude='fsl/refdoc' \
    --exclude='fsl/python/oxford_asl' \
    --exclude='fsl/data/possum' \
    --exclude='fsl/data/first' \
    --exclude='fsl/data/mist' \
    --exclude='fsl/data/atlases' \
    --exclude='fsl/data/xtract_data' \
    --exclude='fsl/extras/doc' \
    --exclude='fsl/extras/man' \
    --exclude='fsl/extras/src' \
    --exclude='fsl/src' \
    --exclude='fsl/tcl'

ENV FSLDIR="/opt/fsl" \
    PATH="/opt/fsl/bin:$PATH" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    FSLTCLSH="/opt/fsl/bin/fsltclsh" \
    FSLWISH="/opt/fsl/bin/fslwish" \
    FSLLOCKDIR="" \
    FSLMACHINELIST="" \
    FSLREMOTECALL="" \
    FSLGECUDAQ="cuda.q" \
    POSSUMDIR="/opt/fsl" \
    LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/opt/fsl"
    
# Unless otherwise specified each process should only use one thread - nipype
# will handle parallelization
ENV MKL_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

COPY --from=freesurfer/synthstrip@sha256:f19578e5f033f2c707fa66efc8b3e11440569facb46e904b45fd52f1a12beb8b /freesurfer/models/synthstrip.1.pt /opt/freesurfer/models/synthstrip.1.pt

ENV FREESURFER_HOME=/opt/freesurfer

# Create a shared $HOME directory
RUN useradd -m -s /bin/bash -G users mriqc
WORKDIR /home/mriqc
ENV HOME="/home/mriqc"
# Refresh linked libraries
RUN ldconfig
# Installing dev requirements (packages that are not in pypi)
WORKDIR /src/
# Precaching atlases
RUN python -c "from templateflow import api as tfapi; \
               tfapi.get('MNI152NLin2009cAsym', resolution=[1, 2], suffix=['T1w', 'T2w'], desc=None); \
               tfapi.get('MNI152NLin2009cAsym', resolution=[1, 2], suffix='mask',\
                         desc=['brain', 'head']); \
               tfapi.get('MNI152NLin2009cAsym', resolution=1, suffix='dseg', desc='carpet'); \
               tfapi.get('MNI152NLin2009cAsym', resolution=1, suffix='probseg',\
                         label=['CSF', 'GM', 'WM']);\
               tfapi.get('MNI152NLin2009cAsym', resolution=[1, 2], suffix='boldref')"
# Installing MRIQC
COPY . /src/mriqc
ARG VERSION=22.0.1

# Force static versioning within container
RUN echo "${VERSION}" > /src/mriqc/mriqc/VERSION && \
    echo "include mriqc/VERSION" >> /src/mriqc/MANIFEST.in && \
    pip install --no-cache-dir "/src/mriqc[all]"
RUN find $HOME -type d -exec chmod go=u {} + && \
    find $HOME -type f -exec chmod go=u {} + && \
    rm -rf $HOME/.npm $HOME/.conda $HOME/.empty

# Best practices
RUN ldconfig

WORKDIR /tmp/

ARG BUILD_DATE
ARG VCS_REF
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="MRIQC" \
      org.label-schema.description="MRIQC - Automated Quality Control and visual reports for Quality Assessment of structural (T1w, T2w) and functional MRI of the brain" \
      org.label-schema.url="http://mriqc.readthedocs.io" \
      org.label-schema.vcs-ref=e021008 \
      org.label-schema.vcs-url="https://github.com/nipreps/mriqc" \
      org.label-schema.version=22.0.1 \
      org.label-schema.schema-version="1.0"
      
# Run mriqc by default
#ENTRYPOINT ["/opt/conda/bin/mriqc"]
#ENTRYPOINT [ "/bin/bash", "-lc"]
CMD ["/opt/conda/bin/mriqc"]
