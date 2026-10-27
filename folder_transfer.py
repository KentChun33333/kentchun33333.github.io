import base64
import io
import zipfile
from pathlib import Path


def encode_folder(source_dir, output_dir):
    """Create a ZIP and save its Base64 representation."""
    source = Path(source_dir).resolve()
    output = Path(output_dir).resolve()

    if not source.is_dir():
        raise NotADirectoryError(source)

    # Prevent the archive from including itself.
    if output == source or source in output.parents:
        raise ValueError(
            "Output directory must be outside the source folder"
        )

    output.mkdir(parents=True, exist_ok=True)

    zip_path = output / f"{source.name}.zip"
    b64_path = output / f"{source.name}.zip.b64"

    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for path in source.rglob("*"):
            archive.write(
                path,
                path.relative_to(source).as_posix(),
            )

    # Read binary ZIP bytes → encode as text-safe Base64.
    b64_path.write_bytes(
        base64.b64encode(zip_path.read_bytes())
    )

    return zip_path, b64_path


def decode_folder(base64_file, destination):
    """Decode Base64, validate the ZIP, then extract its contents."""
    encoded = Path(base64_file).read_bytes()

    # Allow line breaks in the Base64 text.
    zip_bytes = base64.b64decode(
        b"".join(encoded.split()),
        validate=True,
    )

    destination = Path(destination).resolve()

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        # Reject paths that would escape the destination.
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise ValueError(
                    f"Unsafe archive path: {member.filename}"
                )

        bad_file = archive.testzip()
        if bad_file is not None:
            raise ValueError(
                f"Corrupted ZIP member: {bad_file}"
            )

        # Require a new destination to avoid overwriting existing files.
        destination.mkdir(parents=True, exist_ok=False)
        archive.extractall(destination)

    return destination

zip_path, b64_path = encode_folder(
    source_dir="kent_agent_1026",
    output_dir="transfer",
)

print(f"ZIP:    {zip_path}")
print(f"Base64: {b64_path}")


#
#folder = decode_folder(
#    base64_file="kent_agent_1026.zip.b64",
#    destination="kent-agent-restored",
#)
#print(f"Recovered folder: {folder}")
