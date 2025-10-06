from flask import Flask, render_template, request, send_file, Response
from io import BytesIO
from cconv import convert_c_to_cpp, convert_cpp_to_c

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        code = request.form.get("code", "")
        direction = request.form.get("direction", "c2cpp")
        filename = request.form.get("filename", "converted")
        if direction == "c2cpp":
            out = convert_c_to_cpp(code)
            ext = "cpp"
        else:
            out = convert_cpp_to_c(code)
            ext = "c"
        if request.form.get("download"):
            bio = BytesIO(out.encode("utf-8"))
            bio.seek(0)
            return send_file(
                bio,
                as_attachment=True,
                download_name=f"{filename}.{ext}",
                mimetype="text/plain",
            )
        return render_template("index.html", code=code, out=out, direction=direction)
    return render_template("index.html", code="", out="", direction="c2cpp")


@app.route("/healthz")
def healthz():
    return Response("ok", status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
