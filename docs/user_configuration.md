# User Configuration and Storage Overrides

## Overview

JPFM separates configuration into two layers:

1. Core application configuration that the user is not expected to edit regularly.
   This lives in [config/config.yaml](config/config.yaml).
2. User-configurable defaults for behavior such as pruning rules and learned words.
   These are stored in [jpfm/config/user_config_defaults.yaml](jpfm/config/user_config_defaults.yaml).

## Override behavior

The application loads configuration in this order:

1. The base application config from [config/config.yaml](config/config.yaml)
2. The package-level user default values from [jpfm/config/user_config_defaults.yaml](jpfm/config/user_config_defaults.yaml)
3. Any YAML overrides found in the storage directory, such as [storage/config/user_config.yaml](storage/config/user_config.yaml)

This allows users to keep their own overrides in the storage tree without editing files under the package directory.

## Example override file

A user can add a file such as [storage/config/user_config.yaml](storage/config/user_config.yaml) with content like:

```yaml
history_import:
  pruning_rules:
    - type: prohibited_characters
      value: "*"
  learned_words:
    - 食べる
```

## Notes

- Values in [jpfm/config/user_config_defaults.yaml](jpfm/config/user_config_defaults.yaml) are the package defaults.
- Values saved under the storage tree are the user override layer.
- This pattern keeps user-specific settings out of the package tree and makes them easier to manage locally.
