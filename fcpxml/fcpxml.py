from typing import Self, Optional, Tuple, Union, Callable, Any

Numeric = Union[int, float]
def num(s: str) -> Numeric:
    try:
        return int(s)
    except ValueError:
        return float(s)

def listify(fn: Callable[[dict], Any], d: Union[dict, list[dict]]) -> list[dict]:
    if type(d) is list:
        return list(map(fn, d))
    else:
        return [fn(d)]

class Rate:
    fps: int
    ntsc: bool

    def parse(d: dict) -> Self:
        r = Rate()
        r.fps = d["timebase"]
        r.ntsc = d["ntsc"]
        return r

    def dump(self) -> dict:
        return {
            "timebase": self.fps,
            "ntsc": str(self.ntsc).upper()
        }

class TimeCode:
    timecode: str
    rate: Rate

    def parse(d: dict) -> Self:
        r = TimeCode()
        r.timecode = d["string"]
        r.rate = Rate.parse(d["rate"])
        return r

    def dump(self) -> dict:
        return {
            "string": self.timecode,
            "frame": "0",
            "displayformat": "NDF",
            "rate": self.rate.dump()
        }

class FilterParameter:
    name: str
    parameterid: str
    value: Union[Numeric, Tuple[Numeric, Numeric]]
    valuemin: Optional[Numeric]
    valuemax: Optional[Numeric]

    def parse(d: dict) -> Self:
        r = FilterParameter()
        r.name = d["name"]
        r.parameterid = d["parameterid"]
        if type(d["value"]) is str:
            r.value = num(d["value"])
            r.valuemin = num(d["valuemin"])
            r.valuemax = num(d["valuemax"])
        else:
            r.value = (num(d["value"]["horiz"]), num(d["value"]["vert"]))
        return r

    def dump(self) -> dict:
        if type(self.value) is tuple:
            return {
                "name": self.name,
                "parameterid": self.parameterid,
                "value": {
                    "horiz": self.value[0],
                    "vert": self.value[1]
                }
            }
        else:
            return {
                "name": self.name,
                "parameterid": self.parameterid,
                "value": str(self.value),
                "valuemin": str(self.valuemin),
                "valuemax": str(self.valuemax)
            }

class Filter:
    enabled: bool
    start: int
    end: int
    name: str
    mediatype: str
    effectid: str
    effecttype: str
    effectcategory: str
    parameters: list[FilterParameter]

    def parse(d: dict) -> Self:
        r = Filter()
        r.enabled = d["enabled"] == "TRUE"
        r.start = int(d["start"])
        r.end = int(d["end"])
        r.name = d["effect"]["name"]
        r.mediatype = d["effect"]["mediatype"]
        r.effectid = d["effect"]["effectid"]
        r.effecttype = d["effect"]["effecttype"]
        r.effectcategory = d["effect"]["effectcategory"]
        r.parameters = listify(FilterParameter.parse, d["effect"]["parameter"])
        return r
    
    def dump(self) -> dict:
        return {
            "enabled": str(self.enabled).upper(),
            "start": str(self.start),
            "end": str(self.end),
            "effect": {
                "name": self.name,
                "effectid": self.effectid,
                "effecttype": self.effecttype,
                "mediatype": self.mediatype,
                "effectcategory": self.effectcategory,
                "parameter": list(map(lambda p: p.dump(), self.parameters)),
            }
        }


class Link:
    ref: str
    mediatype: Optional[str]

    def parse(d: dict) -> Self:
        r = Link()
        r.ref = d["linkclipref"]
        r.mediatype = d.get("mediatype", None)
        return r

    def dump(self) -> dict:
        mediatype = { "mediatype": self.mediatype } if self.mediatype is not None else {}
        return {
            "linkclipref": self.ref,
            **mediatype
        }

class SourceTrack:
    mediatype: str
    trackindex: int

    def parse(d: dict) -> Self:
        r = SourceTrack()
        r.mediatype = d["mediatype"]
        r.trackindex = d["trackindex"]
        return r

    def dump(self) -> dict:
        return {
            "mediatype": self.mediatype,
            "trackindex": self.trackindex,
        }

class VideoFormat:
    width: int
    height: int
    pixelaspectratio: str
    rate: Rate
    codecname: Optional[str]

    def parse(d: dict) -> Self:
        d = d["samplecharacteristics"]

        r = VideoFormat()
        r.width = d["width"]
        r.height = d["height"]
        r.pixelaspectratio = d["pixelaspectratio"]
        r.rate = Rate.parse(d["rate"])
        r.codecname = d["codec"].get("name", None)
        return r

    def dump(self) -> dict:
        codecname = { "name": self.codecname } if self.codecname is not None else {}
        return {
            "samplecharacteristics": {
                "width": self.width,
                "height": self.height,
                "pixelaspectratio": self.pixelaspectratio,
                "rate": self.rate.dump(),
                "codec": {
                    **codecname,
                    "appspecificdata": {
                        "appname": "Final Cut Pro",
                        "appmanufacturer": "Apple Inc.",
                        "data": {
                            "qtcodec": None
                        }
                    }
                }
            }
        }

class ClipFileData:
    name: str
    pathurl: str
    duration: int
    rate: Rate
    timecode: TimeCode
    width: int
    height: int
    audiochannels: int

    def parse(d: dict) -> Self:
        r = ClipFileData()
        r.name = d["name"]
        r.pathurl = d["pathurl"]
        r.duration = int(d["duration"])
        r.width = int(d["media"]["video"]["samplecharacteristics"]["width"])
        r.height = int(d["media"]["video"]["samplecharacteristics"]["height"])
        r.audiochannels = int(d["media"]["audio"]["channelcount"])
        r.rate = Rate.parse(d["rate"])
        r.timecode = TimeCode.parse(d["timecode"])
        return r

    def dump(self) -> dict:
        return {
            "duration": str(self.duration),
            "rate": self.rate.dump(),
            "name": self.name,
            "pathurl": self.pathurl,
            "timecode": self.timecode.dump(),
            "media": {
                "video": {
                    "duration": str(self.duration),
                    "samplecharacteristics": {
                        "width": str(self.width),
                        "height": str(self.height),
                    }
                },
                "audio": {
                    "channelcount": str(self.audiochannels)
                }
            }
        }

class ClipFile:
    id: str
    data: Optional[ClipFileData]

    def parse(d: dict) -> Self:
        r = ClipFile()
        r.id = d["@id"]
        if "name" in d:
            r.data = ClipFileData.parse(d)
        else:
            r.data = None
        return r

    def dump(self) -> dict:
        data = self.data.dump() if self.data is not None else {}
        return {
            "@id": self.id,
            **data
        }

class Clip:
    id: str
    name: str
    duration: int
    rate: Rate
    start: int
    end: int
    in_param: int
    out_param: int
    file: ClipFile
    enabled: bool
    compositemode: Optional[str]
    filters: list[Filter]
    links: list[Link]
    comments: Optional[str]
    sourcetrack: Optional[SourceTrack]

    def parse(d: dict) -> Self:
        r = Clip()
        r.id = d["@id"]
        r.name = d["name"]
        r.duration = int(d["duration"])
        r.rate = Rate.parse(d["rate"])
        r.start = int(d["start"])
        r.end = int(d["end"])
        r.in_param = int(d["in"])
        r.out_param = int(d["out"])
        r.file = ClipFile.parse(d["file"])
        r.enabled = d["enabled"] == "TRUE"
        r.compositemode = d.get("compositemode", None)
        r.sourcetrack = SourceTrack.parse(d["sourcetrack"]) if "sourcetrack" in d else None
        r.filters = listify(Filter.parse, d["filter"])
        r.links = listify(Link.parse, d["link"])
        r.comments = d.get("comments", None)
        return r

    def dump(self) -> dict:
        compositemode = { "compositemode": self.compositemode } if self.compositemode is not None else {}
        sourcetrack = { "sourcetrack": self.sourcetrack.dump() } if self.sourcetrack is not None else {}
        return {
            "@id": self.id,
            "name": self.name,
            "duration": str(self.duration),
            "rate": self.rate.dump(),
            "start": str(self.start),
            "end": str(self.end),
            "enabled": str(self.enabled).upper(),
            "in": str(self.in_param),
            "out": str(self.out_param),
            "file": self.file.dump(),
            **compositemode,
            **sourcetrack,
            "filter": list(map(lambda f: f.dump(), self.filters)),
            "link": list(map(lambda l: l.dump(), self.links)),
            "comments": self.comments,
        }
    
    def is_linked_to(self, id: str) -> bool:
        for link in self.links:
            if link.ref == id:
                return True
        return False

class Track:
    clips: list[Clip]
    enabled: bool
    locked: bool

    def parse(d: dict) -> Self:
        r = Track()
        r.enabled = d["enabled"] == "TRUE"
        r.locked = d["locked"] == "TRUE"
        r.clips = listify(Clip.parse, d.get("clipitem", []))
        return r
   
    def dump(self) -> dict:
        return {
            "clipitem": list(map(lambda c: c.dump(), self.clips)),
            "enabled": str(self.enabled).upper(),
            "locked": str(self.locked).upper(),
        } 


class FcpXml:
    name: str
    duration: int
    rate: Rate
    in_param: int
    out_param: int
    timecode: TimeCode
    video_tracks: list[Track]
    video_format: VideoFormat
    audio_tracks: list[Track]

    def parse(d: dict) -> Self:
        r = FcpXml()
        d = d["xmeml"]["sequence"]
        r.name = d["name"]
        r.duration = int(d["duration"])
        r.rate = Rate.parse(d["rate"])
        r.in_param = int(d["in"])
        r.out_param = int(d["out"])
        r.timecode = TimeCode.parse(d["timecode"])
        r.video_tracks = listify(Track.parse, d["media"]["video"]["track"])
        r.video_format = VideoFormat.parse(d["media"]["video"]["format"])
        r.audio_tracks = listify(Track.parse, d["media"]["audio"]["track"])
        return r

    def dump(self) -> dict:
        return {
            "xmeml": {
                "@version": "5",
                "sequence": {
                    "name": self.name,
                    "duration": str(self.duration),
                    "rate": self.rate.dump(),
                    "in": str(self.in_param),
                    "out": str(self.out_param),
                    "timecode": self.timecode.dump(),
                    "media": {
                        "video": {
                            "track": list(map(lambda t: t.dump(), self.video_tracks)),
                            "format": self.video_format.dump()
                        },
                        "audio": {
                            "track": list(map(lambda t: t.dump(), self.audio_tracks))
                        }
                    }
                }
            }
        } 