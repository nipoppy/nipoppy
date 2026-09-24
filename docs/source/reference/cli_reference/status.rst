``nipoppy status``
==================

.. note::
   This command calls the :py:class:`nipoppy.workflows.dataset_status.StatusWorkflow` class from the Python :term:`API` internally.

Use ``--datatype`` to restrict the status table to imaging participant-session
pairs whose manifest ``datatype`` list contains any of the requested, comma-
separated BIDS datatypes, for example ``nipoppy status --datatype dwi,anat``.
Blank, whitespace-only, or comma-only values are ignored and leave the status
table unfiltered.
The manifest is the source of the selection; curation and processing checkpoint
values still come from their existing disk-derived status tables.

.. click:: nipoppy.cli.cli:status
   :prog: nipoppy status
