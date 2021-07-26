import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ApptabComponent } from './apptab.component';

describe('ApptabComponent', () => {
  let component: ApptabComponent;
  let fixture: ComponentFixture<ApptabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ApptabComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ApptabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
