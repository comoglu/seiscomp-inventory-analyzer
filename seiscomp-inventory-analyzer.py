#!/usr/bin/env python3

import sys
import warnings
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
from xml.etree import ElementTree as ET
from collections import defaultdict
from pathlib import Path
import pandas as pd
import json
import matplotlib
matplotlib.use('Agg')

class UnifiedSeisCompAnalyzer:
    def __init__(self, debug=False):
        self.ns = {'sc3': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.12'}
        self.debug = debug
        
        # Lookup dictionaries
        self.sensor_lookup = {}
        self.datalogger_lookup = {}
        self.response_lookup = {}
        self.paz_lookup = {}
        
        # Main storage
        self.unified_data = []

    def parse_inventory(self, xml_file):
        """Parse SeisComP3 XML inventory file"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            inventory = root.find('sc3:Inventory', self.ns)
            if inventory is None:
                raise ValueError("No Inventory element found in XML")

            # First build all lookup tables
            self._build_lookup_tables(inventory)
            
            # Then process networks and stations
            self._process_networks(inventory)

            if self.debug:
                print("\nSuccessfully parsed inventory")
                print(f"Found {len(self.sensor_lookup)} sensors")
                print(f"Found {len(self.datalogger_lookup)} dataloggers")
                print(f"Found {len(self.response_lookup)} responses")
                print(f"Found {len(self.paz_lookup)} PAZ responses")
                print(f"Found {len(self.unified_data)} total streams")

        except Exception as e:
            print(f"Error parsing inventory: {e}", file=sys.stderr)
            if self.debug:
                import traceback
                traceback.print_exc()

    def _get_element_text(self, element, tag):
        """Helper method to get element text with namespace"""
        elem = element.find(f'sc3:{tag}', self.ns)
        return elem.text if elem is not None else None

    def _build_lookup_tables(self, inventory):
        """Build lookup tables for all components"""
        # Build sensor lookup with serial numbers
        for sensor in inventory.findall('.//sc3:sensor', self.ns):
            sensor_id = sensor.get('publicID')
            sensor_info = {
                'sensor_name': sensor.get('name', ''),
                'sensor_description': self._get_element_text(sensor, 'description'),
                'sensor_manufacturer': self._get_element_text(sensor, 'manufacturer'),
                'sensor_model': self._get_element_text(sensor, 'model'),
                'sensor_type': self._get_element_text(sensor, 'type'),
                'sensor_unit': self._get_element_text(sensor, 'unit'),
                'sensor_response': sensor.get('response', ''),
                'sensor_remark': self._get_element_text(sensor, 'remark'),
                'sensor_serial_number_equipment': self._get_element_text(sensor, 'serialNumber'),
            }
            self.sensor_lookup[sensor_id] = sensor_info

        # Build datalogger lookup with serial numbers
        for datalogger in inventory.findall('.//sc3:datalogger', self.ns):
            datalogger_id = datalogger.get('publicID')
            datalogger_info = {
                'datalogger_name': datalogger.get('name', ''),
                'datalogger_description': self._get_element_text(datalogger, 'description'),
                'datalogger_manufacturer': self._get_element_text(datalogger, 'manufacturer'),
                'datalogger_model': self._get_element_text(datalogger, 'model'),
                'datalogger_type': self._get_element_text(datalogger, 'type'),
                'datalogger_remark': self._get_element_text(datalogger, 'remark'),
                'datalogger_serial_number_equipment': self._get_element_text(datalogger, 'serialNumber'),
            }
            
            # Process decimations
            decimations = []
            for decimation in datalogger.findall('.//sc3:decimation', self.ns):
                decimation_info = {
                    'sampleRateNumerator': self._get_element_text(decimation, 'sampleRateNumerator'),
                    'sampleRateDenominator': self._get_element_text(decimation, 'sampleRateDenominator'),
                    'analogueFilterChain': self._get_element_text(decimation, 'analogueFilterChain'),
                    'digitalFilterChain': self._get_element_text(decimation, 'digitalFilterChain'),
                }
                decimations.append(decimation_info)
            
            datalogger_info['decimations'] = decimations
            self.datalogger_lookup[datalogger_id] = datalogger_info

        # Build response lookup
        for response in inventory.findall('.//sc3:response', self.ns):
            self.response_lookup[response.get('publicID')] = {
                'response_name': response.get('name', ''),
                'response_gain': self._get_element_text(response, 'gain'),
                'response_frequency': self._get_element_text(response, 'frequency'),
                'response_gainFrequency': self._get_element_text(response, 'gainFrequency'),
            }

        # Build PAZ lookup
        for paz in inventory.findall('.//sc3:responsePAZ', self.ns):
            self.paz_lookup[paz.get('publicID')] = {
                'paz_type': self._get_element_text(paz, 'type'),
                'paz_gain': self._get_element_text(paz, 'gain'),
                'paz_gainFrequency': self._get_element_text(paz, 'gainFrequency'),
                'paz_normalizationFactor': self._get_element_text(paz, 'normalizationFactor'),
                'paz_normalizationFrequency': self._get_element_text(paz, 'normalizationFrequency'),
                'paz_numberOfPoles': self._get_element_text(paz, 'numberOfPoles'),
                'paz_numberOfZeros': self._get_element_text(paz, 'numberOfZeros'),
            }

    def _process_networks(self, inventory):
        """Process all networks and their components"""
        for network in inventory.findall('.//sc3:network', self.ns):
            network_code = network.get('code', '')
            network_start = self._get_element_text(network, 'start')
            network_end = self._get_element_text(network, 'end')
            
            for station in network.findall('.//sc3:station', self.ns):
                self._process_station(network_code, network_start, network_end, station)

    def _process_station(self, network_code, network_start, network_end, station):
        """Process a station and its components"""
        station_code = station.get('code', '')
        station_start = self._get_element_text(station, 'start')
        station_end = self._get_element_text(station, 'end')
        
        for location in station.findall('.//sc3:sensorLocation', self.ns):
            self._process_location(network_code, network_start, network_end,
                                 station_code, station_start, station_end, location)

    def _process_location(self, network_code, network_start, network_end,
                         station_code, station_start, station_end, location):
        """Process a sensor location and its streams"""
        location_code = location.get('code', '')
        latitude = self._get_element_text(location, 'latitude')
        longitude = self._get_element_text(location, 'longitude')
        elevation = self._get_element_text(location, 'elevation')
        
        for stream in location.findall('sc3:stream', self.ns):
            self._process_stream(network_code, network_start, network_end,
                               station_code, station_start, station_end,
                               location_code, latitude, longitude, elevation,
                               stream)

    def _process_stream(self, network_code, network_start, network_end,
                       station_code, station_start, station_end,
                       location_code, latitude, longitude, elevation,
                       stream):
        """Process a stream and combine all related information"""
        try:
            # Base stream information
            stream_data = {
                'network': network_code,
                'network_start': network_start,
                'network_end': network_end,
                'station': station_code,
                'station_start': station_start,
                'station_end': station_end,
                'location': location_code,
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation,
                'channel': stream.get('code', ''),
                'stream_start': self._get_element_text(stream, 'start'),
                'stream_end': self._get_element_text(stream, 'end'),
                'depth': self._get_element_text(stream, 'depth'),
                'azimuth': self._get_element_text(stream, 'azimuth'),
                'dip': self._get_element_text(stream, 'dip'),
                'gain': self._get_element_text(stream, 'gain'),
                'gainFrequency': self._get_element_text(stream, 'gainFrequency'),
                'gainUnit': self._get_element_text(stream, 'gainUnit'),
                'format': self._get_element_text(stream, 'format'),
                'flags': self._get_element_text(stream, 'flags'),
                'restricted': self._get_element_text(stream, 'restricted'),
                'shared': self._get_element_text(stream, 'shared'),
                
                # Stream-level serial numbers and additional info
                'sensor_serial_number_stream': self._get_element_text(stream, 'sensorSerialNumber'),
                'datalogger_serial_number_stream': self._get_element_text(stream, 'dataloggerSerialNumber'),
                'sensorChannel': self._get_element_text(stream, 'sensorChannel'),
                'dataloggerChannel': self._get_element_text(stream, 'dataloggerChannel'),
                'clockSerialNumber': self._get_element_text(stream, 'clockSerialNumber'),
                'sampleRateNumerator': self._get_element_text(stream, 'sampleRateNumerator'),
                'sampleRateDenominator': self._get_element_text(stream, 'sampleRateDenominator'),
                'clockDrift': self._get_element_text(stream, 'clockDrift'),
                'clockModel': self._get_element_text(stream, 'clockModel'),
            }

            # Add sensor information
            sensor_ref = stream.get('sensor')
            if sensor_ref in self.sensor_lookup:
                stream_data.update(self.sensor_lookup[sensor_ref])

            # Add datalogger information
            datalogger_ref = stream.get('datalogger')
            if datalogger_ref in self.datalogger_lookup:
                datalogger_info = self.datalogger_lookup[datalogger_ref]
                for key, value in datalogger_info.items():
                    if key != 'decimations':
                        stream_data[key] = value
                    else:
                        if value:
                            stream_data['decimation_info'] = json.dumps(value)

            # Process comments
            comments = []
            for comment in stream.findall('.//sc3:comment', self.ns):
                comment_text = self._get_element_text(comment, 'text')
                if comment_text:
                    comments.append(comment_text)
            if comments:
                stream_data['stream_comments'] = '; '.join(comments)

            self.unified_data.append(stream_data)

        except Exception as e:
            print(f"Error processing stream: {e}", file=sys.stderr)
            if self.debug:
                import traceback
                traceback.print_exc()

    def export_to_csv(self, output_dir: str = "."):
        """Export unified data to CSV"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        try:
            if self.unified_data:
                df = pd.DataFrame(self.unified_data)
                
                # Clean up the DataFrame
                df = df.replace({None: '', '': ''})
                
                # Combine serial numbers if they exist at multiple levels
                df['sensor_serial_number'] = df.apply(
                    lambda x: x['sensor_serial_number_stream'] or x['sensor_serial_number_equipment'], 
                    axis=1
                )
                df['datalogger_serial_number'] = df.apply(
                    lambda x: x['datalogger_serial_number_stream'] or x['datalogger_serial_number_equipment'], 
                    axis=1
                )
                
                # Drop the intermediate columns
                df = df.drop(columns=[
                    'sensor_serial_number_stream', 
                    'sensor_serial_number_equipment',
                    'datalogger_serial_number_stream', 
                    'datalogger_serial_number_equipment'
                ])
                
                # Save to CSV
                output_file = output_dir / "unified_inventory_analysis.csv"
                df.to_csv(output_file, index=False)

                if self.debug:
                    print(f"\nSuccessfully exported unified CSV file to {output_file}")
                    print(f"Total records: {len(df)}")
                    print("\nColumns in DataFrame:", df.columns.tolist())
                    print("\nSample of sensor serial numbers:", df['sensor_serial_number'].unique()[:5])
                    print("\nSample of datalogger serial numbers:", df['datalogger_serial_number'].unique()[:5])

        except Exception as e:
            print(f"Error exporting CSV file: {e}", file=sys.stderr)
            if self.debug:
                import traceback
                traceback.print_exc()

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Unified analysis of SeisComP3 inventory XML file')
    parser.add_argument(
        'inventory', help='Path to SeisComP3 XML inventory file')
    parser.add_argument('-o', '--output', help='Output directory for results',
                        default='output')
    parser.add_argument('-d', '--debug', help='Enable debug mode',
                        action='store_true')
    return parser.parse_args()

def main():
    args = parse_arguments()
    analyzer = UnifiedSeisCompAnalyzer(debug=args.debug)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    analyzer.parse_inventory(args.inventory)
    analyzer.export_to_csv(args.output)

if __name__ == "__main__":
    main()
