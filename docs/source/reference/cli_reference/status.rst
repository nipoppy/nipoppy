``nipoppy status``
==================

.. note::
   This command calls the :py:class:`nipoppy.workflows.dataset_status.StatusWorkflow` class from the Python :term:`API` internally.

Use ``--datatype`` to restrict the status table to imaging participant-session
pairs whose manifest ``datatype`` list contains the exact requested BIDS
datatype, for example ``nipoppy status --datatype dwi``. The manifest is the
source of truth for the selection.

.. click:: nipoppy.cli.cli:status
   :prog: nipoppy status
