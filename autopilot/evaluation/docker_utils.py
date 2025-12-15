"""
This file is modified from the original file in SWE-bench repository.
https://github.com/SWE-bench/SWE-bench/blob/main/swebench/harness/docker_utils.py
"""

from __future__ import annotations

import traceback

import docker
import docker.errors


def remove_image(client, image_id, logger=None):
  """
  Remove a Docker image by ID.

  Args:
      client (docker.DockerClient): Docker client.
      image_id (str): Image ID.
      rm_image (bool): Whether to remove the image.
      logger (logging.Logger): Logger to use for output. If None, print to stdout.
  """
  if not logger:
    # if logger is None, print to stdout
    log_info = print  # type: ignore
    log_error = print  # type: ignore
    raise_error = True
  elif logger == "quiet":
    # if logger is "quiet", don't print anything
    log_info = lambda x: None  # type: ignore
    log_error = lambda x: None  # type: ignore
    raise_error = True
  else:
    # if logger is a logger object, use it
    log_error = logger.info
    log_info = logger.info
    raise_error = False
  try:
    log_info(f"Attempting to remove image {image_id}...")
    client.images.remove(image_id, force=True)
    log_info(f"Image {image_id} removed.")
  except docker.errors.ImageNotFound:
    log_info(f"Image {image_id} not found, removing has no effect.")
  except Exception as e:
    if raise_error:
      raise e
    log_error(
      f"Failed to remove image {image_id}: {e}\n{traceback.format_exc()}"
    )


def list_images(client: docker.DockerClient):
  """
  List all images from the Docker client.
  """
  # don't use this in multi-threaded context
  return {tag for i in client.images.list(all=True) for tag in i.tags}


def clean_images(
  client: docker.DockerClient, prior_images: set, cache_level: str, clean: bool
):
  """
  Clean Docker images based on cache level and clean flag.

  Args:
      client (docker.DockerClient): Docker client.
      prior_images (set): Set of images that existed before the current run.
      cache (str): Cache level to use.
      clean (bool): Whether to clean; remove images that are higher in the cache hierarchy than the current
          cache level. E.g. if cache_level is set to env, remove all previously built instances images. if
          clean is false, previously built instances images will not be removed, but instance images built
          in the current run will be removed.
  """
  if cache_level == "all":
    return
  images = list_images(client)
  removed = 0
  print("Cleaning cached images...")
  for image_name in images:
    if should_remove(image_name, cache_level, clean, prior_images):
      try:
        remove_image(client, image_name, "quiet")
        removed += 1
      except Exception as e:
        print(f"Error removing image {image_name}: {e}")
        continue
  print(f"Removed {removed} images.")


def should_remove(
  image_name: str, cache_level: str, clean: bool, prior_images: set
):
  """
  Determine if an image should be removed based on cache level and clean flag.
  """
  # If cache_level is "all", don't remove any images
  if cache_level == "all":
    return False

  existed_before = image_name in prior_images
  if "/" in image_name:
    image_name = image_name.rsplit("/", 1)[-1]
  if image_name.startswith("sweb.base"):
    if cache_level in {"none"} and (clean or not existed_before):
      return True
  elif image_name.startswith("sweb.env"):
    if cache_level in {"none", "base"} and (clean or not existed_before):
      return True
  elif image_name.startswith("swe_bench"):
    if cache_level in {"none", "base", "env"} and (clean or not existed_before):
      return True
  return False
