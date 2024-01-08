"""This post task script is used for denoising frames that have finished rendering
into seperate denoised files."""

import ast
import os
import subprocess

from Deadline.Scripting import *


RENDER_TO_DENOISE = "main"
DENOISABLE_AOVS = [
    "C",
    "albedo",
    "beautyunshadowed",
    "coat",
    "combineddiffuse",
    "combineddiffuseunshadowed",
    "combinedemission",
    "combinedglossyreflection",
    "combinedvolume",
    "directdiffuse",
    "directdiffuseunshadowed",
    "directemission",
    "directglossyreflection",
    "directvolume",
    "glossytransmission",
    "indirectdiffuse",
    "indirectdiffuseunshadowed",
    "indirectemission",
    "indirectglossyreflection",
    "indirectvolume",
    "visiblelights",
    "sss",
]


def __main__(*args):
    """Fetches information and calls the correct functions for denoising"""
    deadline_plugin = args[0]

    job = deadline_plugin.GetJob()
    task = deadline_plugin.GetCurrentTask()

    output_directories = job.OutputDirectories
    output_filenames = job.OutputFileNames

    render_aovs = job.ExtraInfoKeyValues[0]
    render_aov_list = ast.literal_eval(str(render_aovs).replace("RenderAOVs=", ""))

    start_frame = task.GetStartFrame()
    end_frame = task.GetEndFrame()
    frame_numbers = range(start_frame, end_frame + 1)

    (
        directory_to_denoise,
        filename_to_denoise,
    ) = get_denoisable_output_directory_and_filename(
        output_directories, output_filenames
    )

    denoise_frames(
        deadline_plugin,
        frame_numbers,
        render_aov_list,
        filename_to_denoise,
        directory_to_denoise,
    )


def get_denoisable_output_directory_and_filename(
    output_directories: list, output_filenames: list
) -> tuple:
    """Returns the directory with matching filename for denoising"""
    output_directory_index_range = range(0, len(output_directories))

    for index in output_directory_index_range:
        output_directory = output_directories[index]
        output_filename = output_filenames[index]

        if output_directory.endswith(RENDER_TO_DENOISE):
            return output_directory, output_filename


def denoise_frames(
    deadline_plugin,
    frame_numbers: range,
    render_aov_list: str,
    output_filename: str,
    output_directory: str,
) -> None:
    """Goes over each frame in our task and executes the correct denoise command."""
    for frame_num in frame_numbers:
        filename = output_filename.replace("%04d", f"{frame_num:04}")
        main_render_file_path = os.path.join(output_directory, filename)

        # Sometimes the name of the render we want to denoise is used elsewhere in the filename,
        # here we make sure to only change the last instance of the render name in the filename.
        new_denoise_filename = filename[::-1].replace(
            RENDER_TO_DENOISE[::-1], "esioned", 1
        )[::-1]

        denoise_render_file_path = os.path.join(
            f"{output_directory[:-4]}denoise",
            new_denoise_filename,
        )

        arguments = construct_denoise_arguments(render_aov_list)

        path_to_denoiser = (
            "C:/Program Files/Side Effects Software/Houdini 19.5.640/bin/idenoise.exe"
        )
        command_to_run = f"{path_to_denoiser} {main_render_file_path} {denoise_render_file_path} {arguments}"

        deadline_plugin.LogInfo(f"Running denoise command: {command_to_run}")
        subprocess.run(command_to_run)


def construct_denoise_arguments(render_aov_list: list) -> str:
    """Constructs a list of arguments for the idenoiser based on available aovs."""
    aovs_to_denoise = []
    arguments = ""

    for aov in render_aov_list:
        if aov == "beauty":
            aovs_to_denoise.append("C")

        elif aov == "albedo":
            arguments += "-a albedo "
            aovs_to_denoise.append("albedo")

        elif aov == "hitN":
            arguments += "-n N "

        elif aov.startswith("LG_"):
            aovs_to_denoise.append(aov)

        elif aov in DENOISABLE_AOVS:
            aovs_to_denoise.append(aov)

    arguments += f"--aovs {' '.join(aovs_to_denoise)}"

    return arguments
