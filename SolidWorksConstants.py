# Copyright (c) 2017 Thomas Karl Pietrowski
# All values below were checked against swconst.tlb of SolidWorks 2023 (revision 31).

class SolidWorkVersions:
    major_version_name = { 24 : "SolidWorks 2016",
                           25 : "SolidWorks 2017",
                           26 : "SolidWorks 2018",
                           27 : "SolidWorks 2019",
                           28 : "SolidWorks 2020",
                           29 : "SolidWorks 2021",
                           30 : "SolidWorks 2022",
                           31 : "SolidWorks 2023",
                           32 : "SolidWorks 2024",
                           33 : "SolidWorks 2025",
                           34 : "SolidWorks 2026",
                          }

    # The first version that can save as 3MF.
    first_3mf_revision = 25

    @classmethod
    def friendlyName(cls, major_revision):
        return cls.major_version_name.get(major_revision, "SolidWorks (revision {})".format(major_revision))

class SolidWorksEnums:
    class swDocumentTypes_e:
        swDocNONE = 0
        swDocPART = 1
        swDocASSEMBLY = 2
        swDocDRAWING = 3

    class swRebuildOnActivation_e:
        swUserDecision = 0
        swDontRebuildActiveDoc = 1
        swRebuildActiveDoc = 2

    class swUserPreferenceToggle_e:
        swSTLBinaryFormat = 69
        swSTLShowInfoOnSave = 70  # Pops up a modal dialog after saving, which would block an invisible SolidWorks.
        swSTLComponentsIntoOneFile = 72
        swSTLPreview = 191
        sw3MFShowInfoOnSave = 643

    class swUserPreferenceIntegerValue_e:
        swSTLQuality = 78
        swExportStlUnits = 211

    class swUserPreferenceDoubleValue_e:
        swSTLDeviation = 2
        swSTLAngleTolerance = 3

    class swSTLQuality_e:
        # SolidWorks derives "custom" from the deviation and angle tolerance: setting swSTLQuality to 3 is accepted and
        # silently ignored. Restoring a custom setting therefore means restoring those two values.
        swSTLQuality_Coarse = 1
        swSTLQuality_Fine = 2
        swSTLQuality_Custom = 3

    class swLengthUnit_e:
        swMM = 0
        swCM = 1
        swMETER = 2
        swINCHES = 3
        swFEET = 4
        swFEETINCHES = 5
        swANGSTROM = 6
        swNANOMETER = 7
        swMICRON = 8
        swMIL = 9
        swUIN = 10

    class swSaveAsVersion_e:
        swSaveAsCurrentVersion = 0

    class swSaveAsOptions_e:
        swSaveAsOptions_Silent = 1
        swSaveAsOptions_Copy = 2

    # Bits of IDocumentSpecification.Error (swFileLoadError_e) worth explaining to the user.
    file_load_errors = {
        1: "generic error",
        2: "file not found",
        1024: "invalid file type",
        8192: "the file was saved with a newer SolidWorks version",
        262144: "SolidWorks is low on resources",
        2097152: "the file needs to be repaired",
        4194304: "critical data in the file needs to be repaired",
        8388608: "SolidWorks is busy",
    }

    # swFileSaveError_e
    file_save_errors = {
        1: "generic error",
        2: "the target is read-only",
        16: "the target file is locked",
        32: "this file format is not available",
        64: "the model has rebuild errors",
        4096: "saving as this format is not supported",
    }

    @staticmethod
    def describeBits(value, descriptions):
        known = [text for bit, text in descriptions.items() if value & bit]
        return ", ".join(known) if known else "code {}".format(value)
