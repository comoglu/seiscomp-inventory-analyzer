# seiscomp-inventory-analyzer

A comprehensive Python tool for analyzing and extracting information from SeisComP inventory XML files. This tool provides unified output of network, station, sensor, and datalogger information from SeisComP inventory files.

## Features

- **Complete Data Extraction**: Extracts all available information from SeisComP inventory XML files
  - Network details
  - Station information
  - Sensor locations
  - Stream configurations
  - Sensor specifications
  - Datalogger details
  - Response information
  - Serial numbers
  - Clock information

- **Unified Output**: Combines all information into a single, comprehensive CSV file
  - Hierarchical relationships preserved
  - Multiple-level information merged
  - Equipment details consolidated
  - Serial numbers from all levels included

- **Flexible Data Processing**:
  - Handles multiple response types (PAZ, FIR, IIR, Polynomial)
  - Processes decimation information
  - Extracts comments and remarks
  - Preserves timing information

## Prerequisites

- Python 3.7 or higher
- Required Python packages:
  ```
  pandas
  matplotlib
  seaborn
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/comoglu/seiscomp-inventory-analyzer.git
   cd seiscomp-inventory-analyzer
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Basic usage:
```bash
python3 seiscomp-analyzer.py /path/to/inventory.xml
```

With debug information:
```bash
python3 seiscomp-analyzer.py /path/to/inventory.xml -d
```

Specifying output directory:
```bash
python3 seiscomp-analyzer.py /path/to/inventory.xml -o /path/to/output
```

### Command Line Arguments

- `inventory`: Path to the SeisComP inventory XML file (required)
- `-o, --output`: Output directory for results (default: "output")
- `-d, --debug`: Enable debug mode for detailed processing information

## Output

The tool generates a unified CSV file containing all extracted information:

### Main Output File: `unified_inventory_analysis.csv`

Contains columns including but not limited to:
- Network information (code, start/end times)
- Station details (code, location, timing)
- Channel information
- Sensor specifications
- Datalogger details
- Serial numbers
- Response parameters
- Location coordinates
- Timing information

## File Structure

```
seiscomp-inventory-analyzer/
├── README.md
├── requirements.txt
├── seiscomp-analyzer.py
└── examples/
    └── sample_inventory.xml
```

## Example

```bash
python3 seiscomp-analyzer.py /opt/seiscomp/etc/inventory/AU.xml -d
```

Sample output:
```
Successfully parsed inventory
Found 1232 sensors
Found 1256 dataloggers
Found 2492 total streams

Successfully exported unified CSV file to output/unified_inventory_analysis.csv
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
2. Create your feature branch (`git checkout -b featureRequest`)
3. Commit your changes (`git commit -m 'Add some Feature'`)
4. Push to the branch (`git push origin featureRequest`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

For more detailed information about the SeisComP inventory XML structure, please refer to:
- [SeisComP Documentation](https://www.seiscomp.de/doc/base/inventory.html)
- [FDSN Station XML Format](http://www.fdsn.org/xml/station/)

## Author

- [Utku Çomoğlu](https://github.com/comoglu)

## Acknowledgments

- SeisComP community for providing the inventory XML schema
- All contributors who participate in this project

## Support

If you encounter any issues or have questions:
1. Check the [existing issues](https://github.com/comoglu/seiscomp-inventory-analyzer/issues)
2. Create a [new issue](https://github.com/comoglu/seiscomp-inventory-analyzer/issues/new) with a detailed description
3. Contact the maintainers

## To-Do

- [ ] Add support for response analysis
- [ ] Implement visualization features
- [ ] Add support for FDSN StationXML format
- [ ] Create detailed documentation for each field in the output
