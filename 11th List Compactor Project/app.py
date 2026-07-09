
from flask import Flask, render_template, request

app = Flask(__name__)

def compact_list(army_list):

    try:

        def flush_models(output, current_models):

            if not current_models:
                return

            current_models.sort(

                key=lambda model: (
                    int(model.split("x")[0].strip())
                    if "x" in model and model.split("x")[0].strip().isdigit()
                    else 0
                ),
                reverse=True
            )

            output.append("• " + ", ".join(current_models))
            current_models.clear()

        #
        #    print("\nDEBUG:")
        #    print(f"Total lines read: {len(army_list.splitlines())}")

        export_footer = "Exported with EclipseTragg's 11th List Compactor"

        remove_phrases = [
            "Incursion",
            "Strike Force",
            "Onslaught"
        ]

        section_headers = [
            "ATTACHED UNITS",
            "CHARACTERS",
            "BATTLELINE",
            "DEDICATED TRANSPORTS",
            "OTHER DATASHEETS",
            "ALLIED UNITS"
        ]
        lines = army_list.split("\n")

        valid_list = any(
            ("point" in line.lower() or "pts" in line.lower())
            for line in lines
        )

        if not valid_list:
            return None

        already_compacted = any(
            "11th List Compactor" in line
            for line in lines
        )

        if already_compacted:
            return (

                army_list,
                len(army_list),
                len(army_list),
                len(army_list.splitlines()),
                len(army_list.splitlines()),
                0,
                0,
                0
            )

        current_models = []
        output = []

        in_units_section = False

        current_unit_index = None
        in_characters_section = False
        current_unit_remove_big_bullets = False

        current_section = ""

        for line in lines:

            line = line.strip()

            if line.startswith("Exported with"):

                if "App Version:" in line and "Data Version:" in line:

                    try:

                        app_version = line.split("App Version:")[1].split(",")[0].strip()
                        app_version = app_version.split()[0]

                        data_version = line.split("Data Version:")[1].strip()

                        export_footer = (
                            f"Exported with EclipseTragg's 11th List Compactor "
                            f"(WH App {app_version} DV {data_version.replace('v', '')})"
                        )

                    except Exception:
                        pass

                continue

            # Skip blank lines
            if not line:
                continue

            # -------- HEADER --------

            if not in_units_section:

                if line.upper() in section_headers:
                    in_units_section = True

                else:
                    if any(phrase in line for phrase in remove_phrases):
                        continue

                    output.append(line)
                    continue

            # -------- UNIT SECTION --------

            # Skip "Attached unit 1", "Attached unit 2", etc.
            if line.lower().startswith("attached unit "):
                flush_models(output, current_models)

                # Don't add a blank line before the first attached unit
                if current_unit_index is not None:
                    output.append("")

                continue

            if line.upper() in section_headers:
                flush_models(output, current_models)

                current_section = line
                in_characters_section = (line == "CHARACTERS")

                output.append("")
                output.append(line.upper())

                continue

            # Unit header
            if "points)" or "pts)" in line.lower():

                flush_models(output, current_models)

                output.append(line)

                current_unit_index = len(output) - 1

                # Start every unit as NOT stripping bullets
                current_unit_remove_big_bullets = False

                if current_section in [
                    "CHARACTERS",
                    "DEDICATED TRANSPORTS",
                    "ALLIED UNITS"
                ]:
                    current_unit_remove_big_bullets = True

                continue

            # Add Leader / Bodyguard tag directly to unit line
            if "Attached as:" in line:

                if current_unit_index is not None:

                    if "Leader" in line:
                        output[current_unit_index] += " - Leader"
                        current_unit_remove_big_bullets = True

                    elif "Bodyguard" in line:
                        output[current_unit_index] += " - Bodyguard"

                    elif "Support" in line:
                        output[current_unit_index] += " - Support"
                        current_unit_remove_big_bullets = True

                continue

            # Add Warlord tag directly to unit line
            if "Warlord" in line:

                if current_unit_index is not None:
                    output[current_unit_index] += " - Warlord"

                continue

            # Remove equipment lines
            if line.startswith("◦"):
                continue

            # Keep model count lines

            # Add Enhancement tag directly to unit line
            if (
                    "enhancement:" in line.lower()
                    or "enhancements:" in line.lower()
                    or (
                    "+" in line
                    and "pts" in line.lower()
                    and line.startswith("•")
            )
            ):

                if current_unit_index is not None:

                    if "enhancement" in line.lower():

                        enhancement = (
                            line.replace("•", "")
                            .replace("Enhancement:", "")
                            .replace("Enhancements:", "")
                            .strip()
                        )

                    else:
                        enhancement = (
                            line.replace("•", "")
                            .split("(")[0]
                            .strip()
                        )

                    output[current_unit_index] += f", Enh: {enhancement}"

                continue

            if current_unit_remove_big_bullets and line.startswith("•"):
                continue

            if line.startswith("•"):
                cleaned_line = line.replace("• ", "")

                parts = cleaned_line.split()

                if parts and parts[0].endswith("x"):

                    number = parts[0][:-1]

                    if number.isdigit():
                        current_models.append(cleaned_line)

                continue

        flush_models(output, current_models)

        result = "\n".join(output)

        result += "\n\n" + export_footer

        original_characters = len(army_list)
        compacted_characters = len(result)

        character_reduction = round(
            (1 - compacted_characters / original_characters) * 100,
            1
        ) if original_characters > 0 else 0

        original_lines = len(army_list.splitlines())
        compacted_lines = len(result.splitlines())

        line_reduction = round(
            (1 - compacted_lines / original_lines) * 100,
            1
        ) if original_lines > 0 else 0

        reduction_percent = max(character_reduction, line_reduction)

        return (
            result,
            original_characters,
            compacted_characters,
            original_lines,
            compacted_lines,
            character_reduction,
            line_reduction,
            reduction_percent
        )

    except Exception as e:

        print("ERROR:", e)

        return None


@app.route("/", methods=["GET", "POST"])
def home():

    result = ""

    original_characters = 0
    compacted_characters = 0

    original_lines = 0
    compacted_lines = 0

    character_reduction = 0
    line_reduction = 0

    reduction_percent = 0
    error_message = ""

    if request.method == "POST":

        army_list = request.form["army_list"]

        compact_result = compact_list(army_list)

        if compact_result is None:

            error_message = "Error: Invalid Army List Format"

        else:

            (
                result,
                original_characters,
                compacted_characters,
                original_lines,
                compacted_lines,
                character_reduction,
                line_reduction,
                reduction_percent
            ) = compact_result

    return render_template(
        "index.html",
        result=result,
        original_characters=original_characters,
        compacted_characters=compacted_characters,
        original_lines=original_lines,
        compacted_lines=compacted_lines,
        character_reduction=character_reduction,
        line_reduction=line_reduction,
        reduction_percent=reduction_percent,
        error_message = error_message
    )


if __name__ == "__main__":
    app.run(debug=True)
