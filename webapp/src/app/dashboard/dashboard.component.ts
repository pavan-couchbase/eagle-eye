import { Component, OnInit } from '@angular/core';
import {Store} from "@ngrx/store";
import {GetData} from "../shared/actions/ee.actions";
import {Observable} from "rxjs";

@Component({
  selector: 'dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  jobId: string = "";
  cluster_name: string = ""
  build: string = ""
  iter_num: number = 0
  dc_name: string = ""

  getDataSuccess$: Observable<any>;
  getDataData: any;

  getDataError$: Observable<any>;
  getDataError: any;

  hasResults: boolean = false;
  getDataLoading: boolean = false;

  constructor(private store: Store<any>) {
    this.getDataSuccess$ = this.store.select(s => s.getData.data);
    this.getDataSuccess$.subscribe((data: any) => {
      if (data) {
        this.getDataData = {};
        this.getDataData = data;
        this.hasResults = true
      } else {
        this.getDataData = undefined;
        this.hasResults = false
      }
      this.getDataLoading = false;
    })

    this.getDataError$ = this.store.select(s => s.getData.errorMsg);
    this.getDataError$.subscribe((data: any) => {
      if (data) {
        this.getDataError = data;
        this.getDataData = {};
        this.hasResults = true
      } else {
        this.getDataError = undefined;
        this.hasResults = false
      }
      this.getDataLoading = false;
    })
  }

  ngOnInit(): void {
  }

  onClickSearch() {
    this.getDataLoading = true;
    let request = {
      jobId: this.jobId,
      iter_num: this.iter_num,
      dc_name: this.dc_name,
      build: this.build,
      cluster_name: this.cluster_name
    }

    this.store.dispatch(GetData({request: request}))
  }

}
