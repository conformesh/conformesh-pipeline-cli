from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect rejected", headers, fp)


def api_url(value: str) -> str:
    value = value.rstrip("/")
    if not value.startswith("https://") and not value.startswith(("http://127.0.0.1", "http://localhost")):
        raise SystemExit("CONFORMESH_API_URL must use HTTPS (HTTP is allowed only for localhost)")
    return value


def load_config(path: str) -> dict:
    target=Path(path)
    if not target.is_file(): return {}
    result={}
    for raw in target.read_text(encoding="utf-8").splitlines():
        line=raw.split("#",1)[0].strip()
        if not line or line.startswith("-") or ":" not in line: continue
        key,value=line.split(":",1);value=value.strip().strip("'\"")
        if key.strip() in ("schema_version","gate","report_language") and value: result[key.strip()]=value
    if result.get("schema_version","1")!="1": raise RuntimeError("unsupported conformesh.yml schema_version")
    return result


def request(base: str, token: str, method: str, path: str, *, body: bytes | None = None, headers: dict | None = None):
    values = {"Authorization": f"Bearer {token}", "User-Agent": "conformesh-pipeline-cli/1", **(headers or {})}
    try:
        response = urllib.request.build_opener(NoRedirect).open(urllib.request.Request(base + path, data=body, headers=values, method=method), timeout=60)
        raw = response.read()
        return response.status, response.headers, raw
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError(f"Conformesh API HTTP {error.code}: {detail}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"Conformesh API unavailable: {error.reason}") from None


def provider_metadata(args) -> dict:
    environment = os.environ
    if environment.get("GITHUB_ACTIONS"):
        provider="github";repository=environment.get("GITHUB_REPOSITORY", "unknown");commit=environment.get("GITHUB_SHA", "unknown");build_id=environment.get("GITHUB_RUN_ID", "unknown");branch=environment.get("GITHUB_REF_NAME");url=f"{environment.get('GITHUB_SERVER_URL','https://github.com')}/{repository}/actions/runs/{build_id}"
    elif environment.get("GITLAB_CI"):
        provider="gitlab";repository=environment.get("CI_PROJECT_PATH", "unknown");commit=environment.get("CI_COMMIT_SHA", "unknown");build_id=environment.get("CI_PIPELINE_ID", "unknown");branch=environment.get("CI_COMMIT_REF_NAME");url=environment.get("CI_PIPELINE_URL")
    elif environment.get("TF_BUILD"):
        provider="azure";repository=environment.get("BUILD_REPOSITORY_NAME", "unknown");commit=environment.get("BUILD_SOURCEVERSION", "unknown");build_id=environment.get("BUILD_BUILDID", "unknown");branch=environment.get("BUILD_SOURCEBRANCHNAME");url=environment.get("SYSTEM_COLLECTIONURI", "") + environment.get("SYSTEM_TEAMPROJECT", "") + "/_build/results?buildId=" + build_id
    elif environment.get("JENKINS_URL"):
        provider="jenkins";repository=environment.get("GIT_URL", "unknown");commit=environment.get("GIT_COMMIT", "unknown");build_id=environment.get("BUILD_TAG") or environment.get("BUILD_NUMBER", "unknown");branch=environment.get("BRANCH_NAME") or environment.get("GIT_BRANCH");url=environment.get("BUILD_URL")
    else:
        provider="generic";repository=args.repository or "unknown";commit=args.commit or "unknown";build_id=args.build_id or str(int(time.time()));branch=args.branch;url=args.build_url
    return {"provider":provider,"repository":repository,"commit":commit,"build_id":build_id,"build_url":url,"branch":branch,"tag":args.tag}


def json_call(base, token, method, path, payload=None, headers=None):
    body = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    _, _, raw = request(base, token, method, path, body=body, headers={"Content-Type":"application/json", **(headers or {})})
    return json.loads(raw)


def create_and_run(args) -> int:
    config=load_config(args.config);args.gate=args.gate or config.get("gate","warn");args.language=args.language or config.get("report_language","en")
    base=api_url(args.api_url);token=os.environ.get("CONFORMESH_PIPELINE_TOKEN")
    if not token: raise RuntimeError("CONFORMESH_PIPELINE_TOKEN is required")
    source=provider_metadata(args);payload={"mode":args.command,"gate_policy":args.gate,"report_language":args.language,"source":source}
    if args.command == "publish": payload["release"]={"release_key":args.release_key,"version":args.version,"lifecycle_state":"released","release_date":args.release_date,"support_ends_at":args.support_ends_at}
    idem=args.idempotency_key or f"{source['provider']}:{source['repository']}:{source['build_id']}:{args.command}"
    run=json_call(base,token,"POST","/v1/pipeline/runs",payload,{"Idempotency-Key":idem});run_id=run["id"]
    artifacts=[("sbom",Path(args.sbom))]
    for value in args.artifact:
        try: kind,path=value.split("=",1)
        except ValueError: raise RuntimeError("--artifact must use kind=path") from None
        artifacts.append((kind,Path(path)))
    for kind,path in artifacts:
        raw=path.read_bytes();query=urllib.parse.urlencode({"kind":kind,"original_name":path.name})
        request(base,token,"POST",f"/v1/pipeline/runs/{run_id}/artifacts?{query}",body=raw,headers={"Content-Type":"application/octet-stream","Content-SHA256":hashlib.sha256(raw).hexdigest()})
    queued=json_call(base,token,"POST",f"/v1/pipeline/runs/{run_id}/complete",{});revision=queued["revision"]
    return wait_and_download(base,token,run_id,revision,Path(args.output),args.timeout)


def wait_and_download(base,token,run_id,revision,output,timeout):
    deadline=time.monotonic()+timeout
    while True:
        status,_,raw=request(base,token,"GET",f"/v1/pipeline/runs/{run_id}/evaluations/{revision}/result")
        result=json.loads(raw)
        if status==200 and "gate_outcome" in result: break
        if result.get("status")=="failed": raise RuntimeError("pipeline evaluation failed; inspect the Conformesh run")
        if time.monotonic()>=deadline: raise RuntimeError("timed out waiting for Conformesh evaluation")
        time.sleep(2)
    output.mkdir(parents=True,exist_ok=True);(output/"conformesh-result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    (output/"conformesh.env").write_text(f"CONFORMESH_RUN_ID={run_id}\nCONFORMESH_EVALUATION_REVISION={revision}\nCONFORMESH_GATE_OUTCOME={result['gate_outcome']}\nCONFORMESH_READY={str(result['ready']).lower()}\n")
    for endpoint,name in (("report.pdf","cra-build-report.pdf"),("evidence.zip","cra-evidence-snapshot.zip")):
        _,_,content=request(base,token,"GET",f"/v1/pipeline/runs/{run_id}/evaluations/{revision}/{endpoint}");(output/name).write_bytes(content)
    if result["ready"] and result["mode"]=="publish":
        _,_,content=request(base,token,"GET",f"/v1/pipeline/runs/{run_id}/evaluations/{revision}/technical-file.zip");(output/"cra-technical-file.zip").write_bytes(content)
    print(json.dumps({"run_id":run_id,"revision":revision,"gate_outcome":result["gate_outcome"],"ready":result["ready"],"output":str(output)},sort_keys=True))
    return 3 if result["gate_outcome"]=="fail" else 0


def recheck(args):
    base=api_url(args.api_url);token=os.environ.get("CONFORMESH_PIPELINE_TOKEN")
    if not token: raise RuntimeError("CONFORMESH_PIPELINE_TOKEN is required")
    queued=json_call(base,token,"POST",f"/v1/pipeline/runs/{args.run}/evaluations",{})
    return wait_and_download(base,token,args.run,queued["revision"],Path(args.output),args.timeout)


def existing(args):
    base=api_url(args.api_url);token=os.environ.get("CONFORMESH_PIPELINE_TOKEN")
    if not token: raise RuntimeError("CONFORMESH_PIPELINE_TOKEN is required")
    return wait_and_download(base,token,args.run,args.revision,Path(args.output),args.timeout)


def verify(path: Path) -> int:
    errors=[]
    try:
        with zipfile.ZipFile(path) as archive:
            expected={line.split("  ",1)[1]:line.split("  ",1)[0] for line in archive.read("SHA256SUMS").decode().splitlines()}
            for name,wanted in expected.items():
                if hashlib.sha256(archive.read(name)).hexdigest()!=wanted: errors.append(name)
    except (zipfile.BadZipFile,KeyError,UnicodeDecodeError) as error: errors.append(str(error))
    print(json.dumps({"valid":not errors,"errors":errors},sort_keys=True));return 0 if not errors else 2


def main() -> int:
    parser=argparse.ArgumentParser(description="Publish build evidence and CRA readiness results to Conformesh")
    parser.add_argument("--api-url",default=os.getenv("CONFORMESH_API_URL","https://conformesh.com"))
    parser.add_argument("--config",default="conformesh.yml")
    commands=parser.add_subparsers(dest="command",required=True)
    for name in ("preview","publish"):
        item=commands.add_parser(name);item.add_argument("--sbom",required=True);item.add_argument("--artifact",action="append",default=[]);item.add_argument("--gate",choices=("warn","strict"));item.add_argument("--language");item.add_argument("--output",default="conformesh-output");item.add_argument("--timeout",type=int,default=600);item.add_argument("--idempotency-key");item.add_argument("--repository");item.add_argument("--commit");item.add_argument("--build-id");item.add_argument("--build-url");item.add_argument("--branch");item.add_argument("--tag")
        if name=="publish": item.add_argument("--release-key",required=True);item.add_argument("--version",required=True);item.add_argument("--release-date");item.add_argument("--support-ends-at")
    item=commands.add_parser("recheck");item.add_argument("--run",required=True);item.add_argument("--output",default="conformesh-output");item.add_argument("--timeout",type=int,default=600)
    for name in ("wait","download"):
        item=commands.add_parser(name);item.add_argument("--run",required=True);item.add_argument("--revision",required=True,type=int);item.add_argument("--output",default="conformesh-output");item.add_argument("--timeout",type=int,default=600 if name=="wait" else 1)
    item=commands.add_parser("verify");item.add_argument("archive",type=Path)
    args=parser.parse_args()
    try:
        if args.command in ("preview","publish"): return create_and_run(args)
        if args.command=="recheck": return recheck(args)
        if args.command in ("wait","download"): return existing(args)
        return verify(args.archive)
    except (RuntimeError,OSError,ValueError) as error:
        print(f"conformesh: {error}",file=sys.stderr);return 2


if __name__ == "__main__": raise SystemExit(main())
