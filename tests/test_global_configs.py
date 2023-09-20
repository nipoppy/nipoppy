import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Mapping

import pytest

from .conftest import global_configs_file, global_configs_for_testing
from nipoppy.base import GlobalConfigs

@pytest.fixture
def global_configs() -> GlobalConfigs:
    return GlobalConfigs(global_configs_file())

@pytest.fixture
def pipeline_configs() -> dict[str, dict]:
    return {
        'fmriprep': {
            'VERSION': '20.2.7',
            'CONTAINER': 'fmriprep-{}.sif',
            'URL': 'https://fmriprep.org/en/stable/'
        },
        'freesurfer': {
            'VERSION': '6.0.1',
            'CONTAINER': 'fmriprep_{}.sif',
            'URL': 'https://surfer.nmr.mgh.harvard.edu/'
        }
    }

@pytest.fixture
def bids_configs() -> dict[str, dict]:
    return {
        'heudiconv': {
            'VERSION': '0.12.2',    
            'CONTAINER': 'heudiconv_{}.sif',
            'URL': 'https://heudiconv.readthedocs.io/en/latest/'
        },
    }

@pytest.fixture
def program_name_and_config() -> dict:
    return (
        'fmriprep',
        {
            'VERSION': '20.2.7',
            'CONTAINER': 'fmriprep-{}.sif',
            'INVOCATION_TEMPLATE': 'fmriprep-{}.json',
            'URL': 'https://fmriprep.org/en/stable/'
        }
    )

@pytest.fixture
def program(program_name_and_config) -> GlobalConfigs.Program:
    name, config = program_name_and_config
    return GlobalConfigs.Program(name=name, config=config)

@pytest.mark.parametrize(
    'param',
    [
        global_configs_file(),
        global_configs_for_testing(Path()),
    ],
)
def test_global_configs_init(param):
    assert GlobalConfigs(param)

@pytest.mark.parametrize(
    'fpath_or_dict',
    [
        global_configs_file(),
        global_configs_for_testing(Path()),
    ],
)
def test_global_configs_get_json_dict(fpath_or_dict):
    assert isinstance(GlobalConfigs._get_json_dict(fpath_or_dict), dict)

def test_global_configs_get_json_dict_not_found():
    with pytest.raises(FileNotFoundError):
        GlobalConfigs._get_json_dict('fake_path.json')

@pytest.mark.parametrize('input', [None, ['x'], 1])
def test_global_configs_get_json_dict_invalid(input):
    with pytest.raises(TypeError):
        GlobalConfigs._get_json_dict(input)

@pytest.mark.parametrize(
    'required_field',
    [
        'DATASET_NAME',
        'DATASET_ROOT',
        'CONTAINER_STORE',
        'SINGULARITY_PATH',
        'SESSIONS',
        'VISITS',
        'BIDS',
        'PROC_PIPELINES',
        'TABULAR',
        'WORKFLOWS',
    ],
)
def test_global_configs_missing_required_field(required_field):

    global_configs = global_configs_for_testing(Path())
    global_configs.pop(required_field)

    with pytest.raises(GlobalConfigs.MissingFieldException, match='Missing field'):
        GlobalConfigs(global_configs)

# TODO test fpath_{manifest,doughnut,derivatives_bagel}    

def test_global_configs_process_programs(pipeline_configs, bids_configs):
    programs = GlobalConfigs._process_programs(pipeline_configs, bids_configs)
    assert isinstance(programs, Mapping)
    assert len(programs) == len(set(pipeline_configs.keys()) | set(bids_configs.keys()))
    for name, program in programs.items():
        assert isinstance(name, str)
        assert isinstance(program, GlobalConfigs.Program)

def test_global_configs_process_programs_duplicates(pipeline_configs):
    with pytest.raises(RuntimeError, match='not unique'):
        GlobalConfigs._process_programs(pipeline_configs, pipeline_configs)

@pytest.mark.parametrize('name', ['fmriprep', 'heudiconv'])
def test_global_configs_get_program(global_configs: GlobalConfigs, name):
    assert global_configs.get_program(name)

def test_global_configs_get_program_invalid(global_configs: GlobalConfigs):
    with pytest.raises(RuntimeError):
       global_configs.get_program('fake_program_name')

@pytest.mark.parametrize('pipeline', ['fmriprep', 'heudiconv'])
def test_global_configs_check_version(global_configs: GlobalConfigs, pipeline):
    assert global_configs.check_version(pipeline)

@pytest.mark.parametrize('pipeline', ['fmriprep', 'heudiconv'])
@pytest.mark.parametrize('dpath_container_store', ['/path/to/containers', '/container_store'])
def test_global_configs_get_fpath_container(global_configs: GlobalConfigs, pipeline, dpath_container_store):
    dpath_container_store = Path(dpath_container_store)
    global_configs.container_store = dpath_container_store
    fpath_container = global_configs.get_fpath_container(pipeline)
    assert dpath_container_store in fpath_container.parents

@pytest.mark.parametrize('pipeline', ['fmriprep', 'heudiconv'])
def test_global_config_get_fpath_invocation_template(global_configs: GlobalConfigs, pipeline):
    assert global_configs.get_fpath_invocation_template(pipeline)

@pytest.mark.parametrize('exception', [KeyError('x'), 'y'])
@pytest.mark.parametrize('message_suffix', ['suffix1', 'suffix2'])
def test_global_config_raise_missing_field_error(global_configs: GlobalConfigs, exception, message_suffix):
    with pytest.raises(GlobalConfigs.MissingFieldException, match=message_suffix):
        global_configs.raise_missing_field_error(exception, message_suffix=message_suffix)

def test_program_init(program_name_and_config):
    name, config = program_name_and_config
    program = GlobalConfigs.Program(name=name, config=config)
    assert program.name == name

@pytest.mark.parametrize('required_field', ['VERSION', 'CONTAINER'])
def test_program_init_missing_required_field(program_name_and_config, required_field):
    name, config = program_name_and_config
    config: dict = config.copy()
    config.pop(required_field)
    with pytest.raises(GlobalConfigs.MissingFieldException, match=required_field):
        GlobalConfigs.Program(name=name, config=config)

@pytest.mark.parametrize('optional_field', ['INVOCATION_TEMPLATE', 'URL'])
def test_program_get_optional_field(program_name_and_config, optional_field):
    name, config = program_name_and_config
    program = GlobalConfigs.Program(name=name, config=config)
    assert program._get_optional_field(optional_field) == config[optional_field]

@pytest.mark.parametrize('optional_field', ['INVOCATION_TEMPLATE', 'URL'])
def test_program_get_optional_field_missing(program_name_and_config, optional_field):
    name, config = program_name_and_config
    config: dict = config.copy()
    config.pop(optional_field)
    program = GlobalConfigs.Program(name=name, config=config)
    with pytest.raises(GlobalConfigs.MissingFieldException, match=optional_field):
        program._get_optional_field(optional_field)

@pytest.mark.parametrize(
    'container,version,expected_result',
    [
        ('fmriprep-{}.sif', '1.0.0', 'fmriprep-1.0.0.sif'),
        ('fmriprep-{}.sif', None, 'fmriprep-.sif'),
        ('fmriprep.sif', '1.0.0', 'fmriprep.sif'),
        ('fmriprep.sif', None, 'fmriprep.sif'),
    ]
)
def test_program_get_fname_container(program_name_and_config, container, version, expected_result):
    name, config = program_name_and_config
    config: dict = config.copy()
    config['CONTAINER'] = container
    if version is not None:
        config['VERSION'] = version
    else:
        config['VERSION'] = ''
    program = GlobalConfigs.Program(name=name, config=config)
    assert program.get_fname_container() == expected_result

@pytest.mark.parametrize(
    'invocation_template,version,expected_result',
    [
        ('fmriprep-{}.json', '1.0.0', Path('fmriprep-1.0.0.json')),
        ('fmriprep-{}.json', None, Path('fmriprep-.json')),
        ('fmriprep.json', '1.0.0', Path('fmriprep.json')),
        ('fmriprep.json', None, Path('fmriprep.json')),
    ]
)
def test_program_get_fpath_invocation_template(program_name_and_config, invocation_template, version, expected_result):
    name, config = program_name_and_config
    config: dict = config.copy()
    config['INVOCATION_TEMPLATE'] = invocation_template
    if version is not None:
        config['VERSION'] = version
    else:
        config['VERSION'] = ''
    program = GlobalConfigs.Program(name=name, config=config)
    assert program.get_fpath_invocation_template() == expected_result

@pytest.mark.parametrize('version', ['1.0.0', ['1.2.3', '2.0.0']])
@pytest.mark.parametrize('name', ['heudiconv', None])
def test_program_process_version(program: GlobalConfigs.Program, version, name):
    assert program._process_version(version)

def test_program_process_version_empty_list(program: GlobalConfigs.Program):
    with pytest.raises(ValueError):
        program._process_version([])

@pytest.mark.parametrize(
        'version_config,program_version,expected_result',
        [
            ('1.0.0', None, '1.0.0'),
            ('1.0.1', '1.0.1', '1.0.1'),
            (['2.2.2', '1.0.1'], None, '2.2.2'),
            (['2.3.4', '5.6.7'], '5.6.7', '5.6.7'),
        ]
    )
def test_program_check_version(program_name_and_config, version_config, program_version, expected_result):
    name, config = program_name_and_config
    config: dict = config.copy()
    config['VERSION'] = version_config
    program = GlobalConfigs.Program(name=name, config=config)
    assert program.check_version(program_version) == expected_result

def test_program_check_version_error(program: GlobalConfigs.Program):
    with pytest.raises(RuntimeError):
        program.check_version('fake_version')

@pytest.mark.parametrize('exception', [KeyError('xyz'), '123'])
def test_program_raise_missing_field_error(program: GlobalConfigs.Program, exception):
    with pytest.raises(GlobalConfigs.MissingFieldException, match=program.name):
        program.raise_missing_field_error(exception)
