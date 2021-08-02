import { Component, OnInit } from '@angular/core';
import { ServerStatus, Stop, Status } from "../shared/actions/ee.actions";
import {Store} from "@ngrx/store";
import {Observable} from "rxjs";

@Component({
  selector: 'server-status',
  templateUrl: './server-status.component.html',
  styleUrls: ['./server-status.component.css']
})
export class ServerStatusComponent implements OnInit {
  serverStatusSuccess$: Observable<any>;
  serverStatusData: any = [];

  serverStatusFail$: Observable<any>;
  serverStatusFailData: string = "";

  startSuccess$: Observable<any>
  startData: any

  stopSuccess$: Observable<any>
  stopData: any;

  stopFail$: Observable<any>
  stopFailData: any;

  stopLoading: boolean = false;

  constructor(private store: Store<any>) {
    this.serverStatusSuccess$ = this.store.select(s => s.serverStatus.data);
    this.serverStatusSuccess$.subscribe((data: any) => {
      if (data) {
        this.serverStatusData = data;
        this.serverStatusFailData = ""
      } else {
        this.serverStatusData = [];
      }
    })

    this.serverStatusFail$ = this.store.select(s => s.serverStatus.error);
    this.serverStatusFail$.subscribe((data: any) => {
      if (data) {
        this.serverStatusFailData = data;
        this.serverStatusData = []
      } else {
        this.serverStatusFailData = ""
      }
    })

    this.startSuccess$ = this.store.select(s => s.start.jobId);
    this.startSuccess$.subscribe((data:any) => {
      if (data) {
        this.startData = data
        this.onClickRefresh()
      } else {
        this.startData = "";
      }
    })

    this.stopSuccess$ = this.store.select(s => s.stop.successMsg);
    this.stopSuccess$.subscribe((data: any) => {
      if (data) {
        this.stopData = data;
        this.stopFailData = ""
        this.onClickRefresh()
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

    this.store.dispatch(ServerStatus())
  }

  ngOnInit(): void {
  }

  onClickRefresh() {
    this.store.dispatch(ServerStatus())
  }

  onClickStop(jobId: string) {
    this.store.dispatch(Stop({jobId: jobId}))
  }
}
