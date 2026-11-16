export default class BaseModel {
  constructor(data = {}) {
    Object.assign(this, data);
  }

  toJSON() {
    return { ...this };
  }

  static fromJSON(data) {
    return new this(data);
  }

  validate() {
    return true;
  }

  clone() {
    return new this.constructor(this.toJSON());
  }
}
