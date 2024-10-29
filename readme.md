# Proxy Server
A simple proxy server with a configurable web interface.

## Description
This project is part of the Network Protocol and Programming course. It includes a Python-based proxy server implemented in [ProxyServer.py](ProxyServer.py). The server features blocking access, censoring content, and replacing content based on rules defined in text files.

## Features
- **Blocking Access**: Block specific URLs.
- **Censoring Content**: Censor specific words or phrases.
- **Replacing Content**: Replace specific words or phrases.
- **Deleting MP4 Resources**: Automatically remove MP4 video resources from web pages.
- **Web Interface**: Configure the proxy server settings via a web interface.

## Usage
Run the proxy server with:
```sh
python ProxyServer.py
```
The proxy runs on port *1234* and the web interface on port *8080*. Configure your browser to use the proxy.

## Configuration
### Web Interface
Access the web interface at `http://localhost:8080`.

### Censoring Content
1. Navigate to "Censor Configuration".
2. Enter words/phrases to censor, one per line.
3. Click "Submit".

Or edit `censorRules.txt` directly.

### Blocking Access
1. Navigate to "Block Access Configuration".
2. Enter URLs to block, one per line.
3. Click "Submit".

Or edit `blockAccessRules.txt` directly.

### Replacing Content
1. Navigate to "Replace Configuration".
2. Enter rules in `word:replacement` format, one per line.
3. Click "Submit".

Or edit `replaceRules.txt` directly.

### Enabling/Disabling Filtering
1. Navigate to "(De)activate Filtering".
2. Select "Enable" or "Disable".
3. Click "Submit".

Or set `filterRule.txt` to `true` or `false`.

## Files
- `ProxyServer.py`: Main proxy server implementation.
- `blockAccessRules.txt`: URLs to block.
- `censorRules.txt`: Words/phrases to censor.
- `replaceRules.txt`: Replace rules in `word:replacement` format.
- `filterRule.txt`: Filter status (`true` or `false`).

## License
This project is licensed under the MIT License.