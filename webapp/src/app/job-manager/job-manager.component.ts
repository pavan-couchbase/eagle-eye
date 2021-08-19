import { Component, OnInit } from '@angular/core';
import {Store} from "@ngrx/store";
import {Start, Status, Stop} from '../shared/actions/ee.actions';
import {Observable} from "rxjs";
import * as defaults from './run_all.json';

@Component({
  selector: 'job-manager',
  templateUrl: './job-manager.component.html',
  styleUrls: ['./job-manager.component.css']
})
export class JobManagerComponent implements OnInit {
  startHost: string = ""
  startClusterName: string = ""
  startConfigFile: any;
  startRunAll: boolean = false;
  startRestUsername: string = "";
  startRestPassword: string = "";
  startSSHUsername: string = "";
  startSSHPassword: string = "";
  startDockerHost: string = "";
  startEmails: string = "";
  startAlertFrequency: number = 3600;
  startRunOne: boolean = false;
  startUploaded: boolean = false;
  defaults: any = defaults;

  startSuccess$: Observable<any>
  startData: any

  startFail$: Observable<any>
  startFail: any

  startLoading: boolean = false

  statusJobId: string = "";

  statusSuccess$: Observable<any>;
  statusData: any = {};

  statusFail$: Observable<any>;
  statusFailData: any;

  statusLoading: boolean = false;

  stopJobId: string = "";

  stopSuccess$: Observable<any>
  stopData: any;

  stopFail$: Observable<any>
  stopFailData: any;

  stopLoading: boolean = false;

  dc_schema = [
    {
      name: "Log Parser",
      function_name: "log_parser",
      run: false,
    },
    {
      name: "CPU Collection",
      function_name: "cpu_collection",
      run: false,
    },
    {
      name: "Memory Collection",
      function_name: "mem_collection",
      run: false,
    },
    {
      name: "Negative Stat Checker",
      function_name: "neg_stat_check",
      run: false,
    },
    {
      name: "Failed Query Checker",
      function_name: "failed_query_check",
      run: false,
    }
  ]

  autoCompleteEmails = [
    {
      "name": "Default",
      "emails": "girish.benakappa@couchbase.com,mihir.kamdar@couchbase.com,ritam@couchbase.com,arunkumar.senthilnathan@couchbase.com,pavithra.mahamani@couchbase.com,chanabasappa.ghali@couchbase.com,sujay.gad@couchbase.com,pierre.regazzoni@couchbase.com,hemant.rajput@couchbase.com"
    }
  ]

  constructor(private store: Store<any>) {
    this.startSuccess$ = this.store.select(s => s.start.jobId);
    this.startSuccess$.subscribe((data:any) => {
      if (data) {
        this.startData = data
        this.startFail = ""
      } else {
        this.startData = "";
      }
      this.startLoading = false;
    })

    this.startFail$ = this.store.select(s => s.start.error);
    this.startFail$.subscribe((data: any) => {
      if (data) {
        this.startFail = data;
        this.startData = ""
      } else {
        this.startFail = "";
      }
      this.startLoading = false;
    })

    this.stopSuccess$ = this.store.select(s => s.stop.successMsg);
    this.stopSuccess$.subscribe((data: any) => {
      if (data) {
        this.stopData = data;
        this.stopFailData = ""
      } else {
        this.stopData = "";
      }
      this.stopLoading = false;
    })

    this.stopFail$ = this.store.select(s => s.stop.errorMsg);
    this.stopFail$.subscribe((data: any) => {
      if (data) {
        this.stopFailData = data
        this.stopData = ""
      } else {
        this.stopFailData = "";
      }
      this.stopLoading = false;
    })

    this.statusSuccess$ = this.store.select(s => s.status.data);
    this.statusSuccess$.subscribe((data: any) => {
      if (data) {
        this.statusData = data
        this.statusFailData = ""
      } else {
        this.statusData = {}
      }
      this.statusLoading = false;
    })

    this.statusFail$ = this.store.select(s => s.status.error);
    this.statusFail$.subscribe((data: any) => {
      if (data) {
        this.statusFailData = data;
        this.statusData = {}
      } else {
        this.statusFailData = "";
      }
      this.statusLoading = false;
    })
  }

  ngOnInit(): void {
  }

  uploadConfigFile(event: any) {
    this.startUploaded = true;
    const fileReader = new FileReader()
    fileReader.readAsText(event.target.files[0], "UTF-8");
    fileReader.onload = () => {
      //this.startConfigFile = JSON.parse(String(fileReader.result));
      this.startConfigFile = String(fileReader.result);
    }
    fileReader.onerror = (error) => {
      console.log(error);
    }
  }

  onClickStart() {
    if (!this.startUploaded) {
      let present = false;
      for (let dc of this.dc_schema) {
        if (dc.run) {
          present = true;
          this.startConfigFile = {};
          break;
        }
      }

      if (present) {
        for (let dc of this.dc_schema) {
          if (dc.run) {
            this.startConfigFile[dc.function_name] = Object.assign({...this.startConfigFile}, this.defaults[dc.function_name])
          }
        }
        this.startConfigFile = JSON.stringify(this.startConfigFile);
      }

    }

    this.startLoading = true;
    let request = {
      host: this.startHost,
      clustername: this.startClusterName,
      configfile: this.startConfigFile,
      runAll: this.startRunAll,
      restusername: this.startRestUsername, restpassword: this.startRestPassword,
      sshusername: this.startSSHUsername, sshpassword: this.startSSHPassword,
      dockerhost: this.startDockerHost,
      emails: this.startEmails,
      alertfrequency: this.startAlertFrequency,
      runOne: this.startRunOne
    }

    this.store.dispatch(Start({request: request}));
  }

  onClickStop() {
    this.stopLoading = true;
    this.store.dispatch(Stop({jobId: this.stopJobId}))
  }

  onClickStatus() {
    this.statusLoading = true;
    this.store.dispatch(Status({jobId: this.statusJobId}))
  }
}
