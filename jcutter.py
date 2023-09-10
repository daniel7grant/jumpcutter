import argparse
import json
import xmltodict
from fcpxml.fcpxml import FcpXml
from typing import Optional

parser = argparse.ArgumentParser(description='Modifies a timeline file to collapse clips to J-cuts.')
parser.add_argument('--input_file', required=True, type=str, help='the timeline you want modified')
parser.add_argument('--output_file', type=str, help='the timeline containing the J-cuts')

args = parser.parse_args()

input_file = args.input_file
output_file = input_file.replace(".xml", "_result.xml")
if args.output_file is not None:
	output_file = args.output_file

print(input_file, output_file)

f: Optional[FcpXml] = None
with open(input_file, "r") as infile:
	d = xmltodict.parse(infile.read())
	f = FcpXml.parse(d)

with open(output_file, "w") as outfile:
	d = f.dump()
	outfile.write(xmltodict.unparse(d, pretty=True))

