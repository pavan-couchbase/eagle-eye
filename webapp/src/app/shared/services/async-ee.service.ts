import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from "@angular/common/http";
import {Observable} from "rxjs";
import {map, catchError} from "rxjs/operators";

//let EERestAPIUrl = 'http://172.23.105.233:5000'
let EERestAPIUrl = 'http://' + self.location.host.split(':')[0] +':5000'

@Injectable({
  providedIn: 'root'
})
export class EEService {

  constructor(private http: HttpClient) {}

  start(host: string,
        clustername: string,
        configfile: any,
        runAll: boolean,
        restusername: string, restpassword: string,
        sshusername: string, sshpassword: string,
        dockerhost: string,
        emails: string,
        alertfrequency: number,
        runOne: boolean): Observable<any> {
    let apiUrl = EERestAPIUrl + "/start";
    let headers = new HttpHeaders();
    let params = new HttpParams();

    // add to the header for parameters
    params = params.set("host",host);
    params = params.set("clustername", clustername);
    if (configfile != {} && configfile)
      params = params.set("configfile", configfile);
    if (runAll)
      params = params.set("runall", runAll);
    if (restusername != "" && restpassword != "") {
      params = params.set("restusername", restusername);
      params = params.set("restpassword", restpassword);
    }
    if (sshusername != "" && sshpassword != "") {
      params = params.set("sshusername", sshusername);
      params = params.set("sshpassword", sshpassword);
    }
    if (dockerhost != "")
      params = params.set("dockerhost", dockerhost);
    if (emails != "")
      params = params.set("emails", emails);
    if (alertfrequency > 0 && alertfrequency != 3600)
      params = params.set("alertfrequency", alertfrequency);
    if (runOne) {
      params = params.set("runone", 1);
    }

    return this.executeRequest(apiUrl, headers, params)
  }

  stop(id: string): Observable<any> {
    let apiUrl = EERestAPIUrl + "/stop";
    let headers = new HttpHeaders();
    let params = new HttpParams();

    params = params.set("id",id);

    return this.executeRequest(apiUrl, headers, params)
  }

  status(id: string): Observable<any> {
    let apiUrl = EERestAPIUrl + "/status";
    let headers = new HttpHeaders();
    let params = new HttpParams();

    params = params.set("id",id);

    return this.executeRequest(apiUrl, headers, params)
  }

  getData(id: string, iter_num: number, dc_name: string, build: string, cluster_name: string): Observable<any> {
    let apiUrl = EERestAPIUrl + "/get-data";
    let headers = new HttpHeaders();
    let params = new HttpParams();

    headers.set("Access-Control-Allow-Origin", "true")

    // add to the header for parameters
    if (id != "")
      params = params.set("id",id);
    if (build != "")
      params = params.set("build",build)
    if (cluster_name != "")
      params = params.set("cluster-name",cluster_name)

    if (iter_num > 0)
      params = params.set("iter-num",iter_num)
    if (dc_name != "")
      params = params.set("data-collector-name",dc_name)

    return this.executeRequest(apiUrl, headers, params)
  }

  serverStatus(): Observable<any> {
    let apiUrl = EERestAPIUrl + "/server-status";
    let headers = new HttpHeaders();
    let params = new HttpParams();

    return this.executeRequest(apiUrl, headers, params);

  }

  uploadSupportal(id: string, iteration: number): Observable<any> {
    let apiUrl = EERestAPIUrl + "/upload-supportal"
    let headers = new HttpHeaders();
    let params = new HttpParams();

    params = params.set("id", id);
    params = params.set("iteration", iteration);

    return this.executeRequest(apiUrl, headers, params);
  }

  executeRequest(apiUrl: string, headers: any, params: any): Observable<any> {
    return this.http.post<any>(apiUrl, {}, ({headers: headers, params: params}))
      .pipe(map((response: Response) => { return response; }),
        catchError((error: any) => this.handleError(error)))
  }

  private handleError(error: any): Promise<any> {
    console.log("request error")
    console.log(error)
    return Promise.reject(error.error || error)
  }
}
