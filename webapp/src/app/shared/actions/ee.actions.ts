import {Action, createAction, props} from "@ngrx/store";

export const START =            '[START] Start eagle-eye';
export const START_SUCCESS =    '[START] Start eagle-eye success';
export const START_FAIL =       '[START] Start eagle-eye fail';

export const STOP =             '[STOP] Stop eagle-eye';
export const STOP_SUCCESS =     '[STOP] Stop eagle-eye success';
export const STOP_FAIL =        '[STOP] Stop eagle-eye fail';

export const STATUS =           '[STATUS] Status of eagle-eye';
export const STATUS_SUCCESS =   '[STATUS] Status of eagle-eye success';
export const STATUS_FAIL =      '[STATUS] Status of eagle-eye fail';

export const GETDATA =          '[GetData] Get data from eagle-eye';
export const GETDATA_SUCCESS =  '[GetData] Get data from eagle-eye success';
export const GETDATA_FAIL =     '[GetData] Get data from eagle-eye fail';

export interface StartRequest {
  host: string,
  clustername: string,
  configfile: any,
  restusername: string, restpassword: string,
  sshusername: string, sshpassword: string,
  dockerhost: string,
  emails: string,
  alertfrequency: number,
}

export interface GetDataRequest {
  jobId: string,
  iter_num: number,
  dc_name: string,
  build: string,
  cluster_name: string
}

export const Start = createAction(
  START,
  props<{
    request: StartRequest
  }>()
)

export const StartSuccess = createAction(
  START_SUCCESS,
  props<{
    jobId: string
  }>()
)

export const StartFail = createAction(
  START_FAIL,
  props<{
    error: string
  }>()
)

export const Stop = createAction(
  STOP,
  props<{
    jobId: string
  }>()
)

export const StopSuccess = createAction(
  STOP_SUCCESS,
  props<{
    msg: string
  }>()
)

export const StopFail = createAction(
  STOP_FAIL,
  props<{
    msg: string
  }>()
)

export const Status = createAction(
  STATUS,
  props<{
    jobId: string
  }>()
)

export const StatusSuccess = createAction(
  STATUS_SUCCESS,
  props<{
    data: any
  }>()
)

export const StatusFail = createAction(
  STATUS_FAIL,
  props<{
    error: string
  }>()
)

export const GetData = createAction(
  GETDATA,
  props<{
    request: GetDataRequest
  }>()
)

export const GetDataSuccess = createAction(
  GETDATA_SUCCESS,
  props<{
    data: any
  }>()
)

export const GetDataFail = createAction(
  GETDATA_FAIL,
  props<{
    Msg: string
  }>()
)
