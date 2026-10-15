all
# Exclude some rule to preserve current Nipoppy style
exclude_rule 'MD002' # Enforces H1 first; breaks GitHub PR template where PR title is already H1.
exclude_rule 'MD007' # Enforces 3-space list indent; breaks existing 2- and 4-space nested lists across docs.
exclude_rule 'MD013' # Enforces 80-char line limit.
exclude_rule 'MD014' # Forbids '$' prompts without output; degrades Pygments syntax highlighting in console blocks.
exclude_rule 'MD028' # Forbids blank lines in blockquotes; breaks MyST admonition parsing for adjacent alert boxes.
exclude_rule 'MD029' # Enforces '1. 1. 1.' numbering; churns docs written with explicit sequential numbering.
exclude_rule 'MD033' # Forbids inline HTML; inline HTML needed for e.g. YouTube videos, some images, team/contributor tables.
exclude_rule 'MD040' # Fenced code blocks should have a language.
exclude_rule 'MD041' # First line in file should be a top level header.

# Allow headers ending with '?' or '!' (e.g., "Why Nipoppy?").
rule 'MD026', :punctuation => '.,;:'
