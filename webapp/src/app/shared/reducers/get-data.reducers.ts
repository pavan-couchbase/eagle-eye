import * as eeActions from '../actions/ee.actions';
import {Action,createReducer, on} from "@ngrx/store";

export interface State {
  jobId: string,
  iter_num: number,
  dc_name: string,
  build: string,
  cluster_name: string,
  data: any[],
  errorMsg: string
}

export const initialState: State = {
  jobId: "",
  iter_num: 0,
  dc_name: "",
  build: "",
  cluster_name: "",
  data: [],
  errorMsg: ""
}

const statusReducer = createReducer(
  initialState,
  on(eeActions.GetData, (state, {request}) => ({
    ...state,
    jobId: request.jobId,
    iter_num: request.iter_num,
    dc_name: request.dc_name,
    build: request.build,
    cluster_name: request.cluster_name
  })),
  on(eeActions.GetDataSuccess, (state, {data}) => ({
    ...state,
    data: data
  })),
  on(eeActions.GetDataFail, (state, {Msg}) => ({
    ...state,
    errorMsg: Msg
  }))
)

export function reducer(state: State | undefined, action: Action) {
  return statusReducer(state, action)
}
