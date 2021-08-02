import {Component, Input, OnInit} from '@angular/core';

@Component({
  selector: 'data-viewer',
  templateUrl: './data-viewer.component.html',
  styleUrls: ['./data-viewer.component.css']
})
export class DataViewerComponent implements OnInit {
  @Input() data: any;

  parsed_data: any[] = [];
  timeseries_data: any = {};

  data_collectors = {
    "log_parser": true,
    "mem_collection": true,
    "cpu_collection": true,
    "neg_stat_check": true,
    "failed_query_check": true,
    "logs": true,
    "cluster_summary": true
  };

  jobId: any;
  build: any;
  clustername: any;

  constructor() {
  }

  ngOnInit(): void {
  }

  ngOnChanges() {
    this.data = this.data
    this.parsed_data = []

    this.timeseries_data = {}
    let arrayForSort = [...this.data]
    arrayForSort.sort((a: any , b: any) => (a.iteration > b.iteration) ? 1 : -1)

    if (arrayForSort.length > 0) {
      this.jobId = arrayForSort[0]['id'];
      this.build = arrayForSort[0]['build'];
      this.clustername = arrayForSort[0]['cluster_name'];
    }

    for (let doc of arrayForSort) {
      let to_add: any = {
        id: doc['id'],
        iteration: doc['iteration'],
        cluster_name: doc['cluster_name'],
        build: doc['build'],
      };
      this.timeseries_data[doc['iteration']] = []
      let collected = []
      for (let key of Object.keys(doc)) {
        if (key in this.data_collectors) {
          let dc_doc = Object.assign({}, doc[key], {'name': key})

          if (doc[key]['type'] == 'time_series') {
            let time_series: any = {};

            let seen_nodes: any = {};

            for (let point of doc[key]['data']) {
              if (!(point['node'] in time_series)) {
                time_series[point['node']] = {'name': point['node'], 'series': []}
              }

              let year = +point['timestamp'].split('T')[0].split('-')[0]
              let month = +point['timestamp'].split('T')[0].split('-')[1]
              let day = +point['timestamp'].split('T')[0].split('-')[2]
              let hour = +point['timestamp'].split('T')[1].split(':')[0]
              let min = +point['timestamp'].split('T')[1].split(':')[1]
              let sec = +point['timestamp'].split('T')[1].split(':')[2]

              time_series[point['node']]['series'].push({"value": point['usage'], 'name': new Date(year, month, day, hour, min, sec)})
            }
            let temp = []
            for (let node of Object.keys(time_series)) {
              temp.push(time_series[node])
            }
            Object.assign(dc_doc, {"timeseries": temp})


          }

          collected.push(dc_doc)

        }
      }
      to_add['collected'] = collected;
      this.parsed_data.push(to_add);
    }
  }

}
